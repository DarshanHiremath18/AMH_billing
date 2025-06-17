from flask import Flask, render_template, request, redirect, url_for
from flask_pymongo import PyMongo
from datetime import datetime
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://Darshan:Dah123@cluster0.s1rmloi.mongodb.net/chilli_shop?retryWrites=true&w=majority&appName=Cluster0"
mongo = PyMongo(app)

# Home Page
@app.route('/')
def home():
    lots = list(mongo.db.lots.find())

    # Enrich each lot with farmer details
    for lot in lots:
        farmer = mongo.db.farmers.find_one({'_id': lot['farmer_id']})
        if farmer:
            lot['farmer_name'] = farmer.get('name', '')
            lot['city'] = farmer.get('city', '')
            lot['phone'] = farmer.get('phone', '')
        else:
            lot['farmer_name'] = 'Unknown'
            lot['city'] = ''
            lot['phone'] = ''

    return render_template('dashboard.html', lots=lots)


# Add Farmer & Create Lot

@app.route('/add-farmer', methods=['GET', 'POST'])
def add_farmer():
    if request.method == 'POST':
        district = request.form['District']
        city = request.form['city']
        name = request.form['name']
        date = request.form['calendar_date']
        bag_count = int(request.form['bag_count'])
        bag_weights = request.form.getlist('bag_weights')
        bag_checked = request.form.getlist('bag_checked')

        # Optional: Convert weights and mark which ones are checked
        bag_data = []
        for i in range(bag_count):
            weight = float(bag_weights[i]) if i < len(bag_weights) and bag_weights[i] else 0
            checked = True if i < len(bag_checked) else False
            bag_data.append({'weight': weight, 'checked': checked})

        # Get or insert farmer
        farmer = mongo.db.farmers.find_one({'name': name, 'city': city, 'district': district})
        farmer_id = farmer['_id'] if farmer else mongo.db.farmers.insert_one({
            'name': name, 'city': city, 'district': district, 'date':date , 'bag_count':bag_count , 'bag_weights':bag_weights 
        }).inserted_id

        # Generate lot number for the selected date
        last_lot = mongo.db.lots.find_one({'calendar_date': date}, sort=[('lot_no', -1)])
        lot_no = (last_lot['lot_no'] + 1) if last_lot else 1

        # Save to lots collection
        mongo.db.lots.insert_one({
            'lot_no': lot_no,
            'calendar_date': date,
            'district': district,
            'city': city,
            'farmer_id': farmer_id,
            'bag_count': bag_count,
            'bags': bag_data
        })

        return redirect(url_for('home'))

    # GET method
    districts = mongo.db.farmers.distinct('district')
    return render_template('add_farmer.html', District=districts)




# AJAX: Get cities by district
@app.route('/get-cities', methods=['POST'])
def get_cities():
    district = request.json.get('district')
    cities = mongo.db.parties.distinct('city', {'District': district})
    return {'cities': cities}


# AJAX: Get farmers by city and district
@app.route('/get-farmers', methods=['POST'])
def get_farmers():
    city = request.json.get('city')
    district = request.json.get('district')
    farmers = list(mongo.db.parties.find({'city': city, 'District': district}, {'name': 1, 'phone': 1, '_id': 0}))
    return {'farmers': farmers}



# Generate Lot Number
def generate_lot_number():
    total = mongo.db.lots.count_documents({})
    return f"LOT{str(total + 1).zfill(3)}"

# Add Bag Weights
@app.route('/add-bags/<lot_id>', methods=['GET', 'POST'])
def add_bags(lot_id):
    lot = mongo.db.lots.find_one({'_id': ObjectId(lot_id)})
    if request.method == 'POST':
        new_weight = float(request.form['weight'])
        mongo.db.lots.update_one(
            {'_id': ObjectId(lot_id)},
            {'$push': {'bag_weights': new_weight}}
        )
        return redirect(url_for('add_bags', lot_id=lot_id))
    return render_template('add_bags.html', lot=lot)

# Edit Bag Weight
@app.route('/edit-weight/<lot_id>/<int:index>', methods=['POST'])
def edit_weight(lot_id, index):
    new_weight = float(request.form['weight'])
    lot = mongo.db.lots.find_one({'_id': ObjectId(lot_id)})
    weights = lot['bag_weights']
    weights[index] = new_weight
    mongo.db.lots.update_one({'_id': ObjectId(lot_id)}, {'$set': {'bag_weights': weights}})
    return redirect(url_for('add_bags', lot_id=lot_id))

# Set Rate and Preview Bill
@app.route('/set-rate/<lot_id>', methods=['GET', 'POST'])
def set_rate(lot_id):
    lot = mongo.db.lots.find_one({'_id': ObjectId(lot_id)})
    if request.method == 'POST':
        rate = float(request.form['rate'])
        mongo.db.lots.update_one({'_id': ObjectId(lot_id)}, {'$set': {'rate_per_100kg': rate}})
        return redirect(url_for('bill_preview', lot_id=lot_id))
    return render_template('set_rate.html', lot=lot)

# Final Bill Preview
@app.route('/bill/<lot_id>')
def bill_preview(lot_id):
    lot = mongo.db.lots.find_one({'_id': ObjectId(lot_id)})
    total_weight = sum(lot['bag_weights'])
    total_amount = (lot['rate_per_100kg'] / 100) * total_weight
    return render_template('bill_preview.html', lot=lot, total_weight=total_weight, total_amount=total_amount)

@app.route('/add-party', methods=['GET', 'POST'])
def add_party():
    if request.method == 'POST':
        data = {
            'type': request.form['type'],
            'first_name': request.form['first_name'],
            'middle_name': request.form.get('middle_name', ''),
            'last_name': request.form['last_name'],
            'city': request.form['city'],
            'District':request.form['District'],
            'short_name': request.form.get('short_name', '') if request.form['type'] == 'Buyer' else '',
            'account_type': request.form['account_type'],
            'account_head': request.form['account_head'],
            'mobile_no': request.form['mobile_no'],
            'address': request.form['address'],
            'aadhar_no': request.form['aadhar_no'],
            'bank_account': request.form['bank_account'],
            'ifsc_code': request.form['ifsc_code'],
            'gst_no': request.form['gst_no']
        }
        mongo.db.parties.insert_one(data)
        return redirect(url_for('home'))
    
    return render_template('add_party.html')
# Add City
@app.route('/add-city', methods=['GET', 'POST'])
def add_city():
    if request.method == 'POST':
        data = {
            'city': request.form['city'],
            'district': request.form['district'],
            'state': request.form['state']
        }
        mongo.db.cities.insert_one(data)
        return redirect(url_for('home'))
    return render_template('add_city.html')

# Add Account Head
@app.route('/add-account-head', methods=['GET', 'POST'])
def add_account_head():
    if request.method == 'POST':
        head_name = request.form['account_head']
        mongo.db.account_heads.insert_one({'account_head': head_name})
        return redirect(url_for('home'))
    return render_template('add_account_head.html')
# Billing Page (form to create a new bill)
@app.route('/billing', methods=['GET', 'POST'])
def billing():
    if request.method == 'POST':
        farmer_id = ObjectId(request.form['farmer'])
        farmer = mongo.db.farmers.find_one({'_id': farmer_id})
        quantity = float(request.form['quantity'])
        rate = float(request.form['rate'])
        total = quantity * rate

        mongo.db.bills.insert_one({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'farmer_id': farmer_id,
            'farmer_name': farmer['name'],
            'city': farmer['city'],
            'quantity': quantity,
            'rate': rate,
            'total': total
        })
        return redirect(url_for('bills'))

    farmers = list(mongo.db.farmers.find())
    return render_template('billing.html', farmers=farmers)

# Bill History
@app.route('/bills')
def bills():
    bills = list(mongo.db.bills.find().sort('date', -1))
    return render_template('bills.html', bills=bills)

# Select Lot for Set Rate
@app.route('/set-rate-select')
def set_rate_selector():
    lots = list(mongo.db.lots.find())
    return render_template('select_lot.html', lots=lots, action='set_rate')

# Select Lot for Bill Preview
@app.route('/bill-preview-select')
def bill_preview_selector():
    lots = list(mongo.db.lots.find())
    return render_template('select_lot.html', lots=lots, action='preview')



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

