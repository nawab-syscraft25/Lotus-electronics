import sqlite3

# Connect to DB (creates if not exists)
conn = sqlite3.connect("lotus_stores.db")
c = conn.cursor()

# Create table
c.execute("""
CREATE TABLE IF NOT EXISTS stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_name TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zipcode TEXT,
    timing TEXT
)
""")

# Store data (name, address, city, state, zip, timing)
stores_data = [
    ("Lotus Electronics Store at Sapna Sangeeta", "13, Sneh Nagar, Sapna Sangeeta Main Road", "Indore", "Madhya Pradesh", "452001", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Old Palasia", "Navneet Darshan Towers, 16/2, Greater Kailash Road, New Palasia", "Indore", "Madhya Pradesh", "452003", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at A.B. Road", "Survey No. 182/2/1, Surya Sadhna, A B Road, MR 9 Rd, Square", "Indore", "Madhya Pradesh", "452011", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Mhow Naka", "282, Appaji Regency, Near Mhow Naka, Annapurna Road, Usha Nagar", "Indore", "Madhya Pradesh", "452009", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Marimata Chauraha", "Shri Krishna Divine 149, Sir Siremal Bafna Marg, Marimata Chauraha", "Indore", "Madhya Pradesh", "452007", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Bicholi Mardana", "Serve No 82/1/2/5 Bicholi Mardana, Near Agarwal Public School", "Indore", "Madhya Pradesh", "452016", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Royal Park", "G-18/19/118/119, Royal Park, Khasra No. 288 Rau AB Road", "Indore", "Madhya Pradesh", "452012", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Dewas Road", "56/2, Dewas Road, Vishala Area", "Ujjain", "Madhya Pradesh", "456010", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at M.P Nagar", "City Center, 1 B/h, Vishal Mega Mart, Indira Press Complex, Zone-I, Maharana Pratap Nagar", "Bhopal", "Madhya Pradesh", "462001", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Kohefiza", "B2, B3, B4 BDA Colony, Lal Ghati, Koh-E-fiza", "Bhopal", "Madhya Pradesh", "462001", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Hoshangabad Road", "Survey No. 352/9, Phoenix Corporate Park Road, Opp. Vrindavan Garden, Bawadiya Kalan", "Bhopal", "Madhya Pradesh", "462026", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Old Campion Ground", "Opp. Old Campion Cricket Ground, E-1, Arera Colony", "Bhopal", "Madhya Pradesh", "462016", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Kolar Road", "1 A , 8 K K Nagar Sarvdharam C Sector, Banjari Colony, Kolar Rd", "Bhopal", "Madhya Pradesh", "462042", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Napier Town", "124, Napier Town, Commercial Automobiles Building, Near Shastri Bridge", "Jabalpur", "Madhya Pradesh", "482001", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Opp Empress Mall", "Mytri Willwos, 3, Opp. Empress Mall, Dr. Bezonji Mehta Road", "Nagpur", "Maharashtra", "440018", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Shankar Nagar, Nagpur", "Platina Enclave, 13, Ambazari Road, Opp. New Wochardt Hospital, Om Sai Nagar, Shivaji Nagar", "Nagpur", "Maharashtra", "440010", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Dobi Nagar", "Khasara Number 48/2 ,Plot no. 82 to 88 , Dobi Nagar , Manewada ring road", "Nagpur", "Maharashtra", "440027", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Jail Road", "R.M. Plaza, Jail Road, Near Kutchery Chowk", "Raipur", "Chhattisgarh", "492001", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Ring Road", "Opposite Corporate Center, 1, Telibandha Ring Road, New Rajendra Nagar", "Raipur", "Chhattisgarh", "492001", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Shankar Nagar, Raipur", "HIG - 24, Sector - 1, Main Road Shankar Nagar", "Raipur", "Chhattisgarh", "492004", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Sairam Business Park", "Block A, Sairam Business Park, GE Road, Krishna Nagar, Supela", "Bhilai", "Chhattisgarh", "490023", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Agrasen Chowk", "Opp Bukhari Petrol Pump, & Hotel Natraj, Near Agrasen Chowk, Link Road", "Bilaspur", "Chhattisgarh", "495001", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at SL Marg", "Plot No. F-1, E-1, E-10/1, 9 to 17, Lal Bahadur Nagar, Unit No.4, SL Marg, JLN Marg", "Jaipur", "Rajasthan", "302018", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Vaishali Nagar", "Plot 281 Vaishali Marg Vaishali Nagar", "Jaipur", "Rajasthan", "302021", "11:30 AM – 09:30 PM (Mon - Sun)"),
    ("Lotus Electronics Store at Vijay Path", "Plot No.121-01, Mansarovar, Vijay Path", "Jaipur", "Rajasthan", "302020", "11:30 AM – 09:30 PM (Mon - Sun)"),
]

# Insert data
c.executemany("INSERT INTO stores (store_name, address, city, state, zipcode, timing) VALUES (?, ?, ?, ?, ?, ?)", stores_data)

conn.commit()
conn.close()

print("Database 'lotus_stores.db' created with store data.")
