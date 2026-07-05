"""Seed script: creates a demo restaurant with sample menu and tables."""
from app.database import SessionLocal, engine, Base
from app.models import Restaurant, Table, MenuCategory, MenuItem, ModifierGroup, ModifierOption

Base.metadata.create_all(bind=engine)
db = SessionLocal()

existing = db.query(Restaurant).filter(Restaurant.slug == "tandoori-flame").first()
if existing:
    print("Restaurant already exists. Skipping seed.")
    db.close()
    exit()

restaurant = Restaurant(
    name="Tandoori Flame",
    slug="tandoori-flame",
    suburb="Harris Park",
    currency="AUD",
    gst_rate=10.0,
    abn="12 345 678 901",
)
db.add(restaurant)
db.flush()

for i in range(1, 13):
    db.add(Table(restaurant_id=restaurant.id, table_number=i))

# Categories
starters = MenuCategory(restaurant_id=restaurant.id, name={"en": "Starters", "hi": "स्टार्टर्स", "zh": "开胃菜"}, sort_order=1)
mains = MenuCategory(restaurant_id=restaurant.id, name={"en": "Mains", "hi": "मुख्य व्यंजन", "zh": "主菜"}, sort_order=2)
breads = MenuCategory(restaurant_id=restaurant.id, name={"en": "Breads", "hi": "रोटी", "zh": "面包"}, sort_order=3)
desserts = MenuCategory(restaurant_id=restaurant.id, name={"en": "Desserts", "hi": "मिठाई", "zh": "甜品"}, sort_order=4)
drinks = MenuCategory(restaurant_id=restaurant.id, name={"en": "Drinks", "hi": "पेय", "zh": "饮料"}, sort_order=5)
db.add_all([starters, mains, breads, desserts, drinks])
db.flush()

items = [
    MenuItem(category_id=starters.id, name={"en": "Samosas (3 pcs)", "hi": "समोसे (3 टुकड़े)", "zh": "萨摩萨三角饺 (3个)"}, description={"en": "Crispy pastry filled with spiced potatoes", "hi": "मसालेदार आलू से भरे कुरकुरे समोसे", "zh": "脆皮糕点，内馅为五香土豆"}, price=8.50, sort_order=1),
    MenuItem(category_id=starters.id, name={"en": "Chicken Tikka", "hi": "चिकन टिक्का", "zh": "烤鸡块"}, description={"en": "Marinated chicken pieces grilled in clay oven", "hi": "मिट्टी के तंदूर में पकाया हुआ मैरीनेटेड चिकन", "zh": "腌制鸡肉块在泥炉中烤制"}, price=14.00, sort_order=2),
    MenuItem(category_id=starters.id, name={"en": "Onion Bhaji", "hi": "प्याज़ के पकौड़े", "zh": "洋葱圈"}, description={"en": "Spiced onion fritters deep fried", "hi": "मसालेदार प्याज के पकौड़े", "zh": "五香洋葱油炸馅饼"}, price=7.00, sort_order=3),
    MenuItem(category_id=mains.id, name={"en": "Butter Chicken", "hi": "बटर चिकन", "zh": "黄油鸡"}, description={"en": "Creamy tomato-based curry with tender chicken", "hi": "मलाईदार टमाटर आधारित करी में नरम चिकन", "zh": "奶油番茄基底的咖喱鸡肉"}, price=22.00, sort_order=1),
    MenuItem(category_id=mains.id, name={"en": "Lamb Rogan Josh", "hi": "लैम्ब रोगन जोश", "zh": "辣炖羊肉"}, description={"en": "Slow-cooked lamb in aromatic Kashmiri gravy", "hi": "सुगंधित कश्मीरी ग्रेवी में धीमी आंच पर पका हुआ मेमना", "zh": "在芳香的开西米尔肉汁中慢炖的羊肉"}, price=24.00, sort_order=2),
    MenuItem(category_id=mains.id, name={"en": "Dal Makhani", "hi": "दाल मखनी", "zh": "黑扁豆咖喱"}, description={"en": "Slow-cooked black lentils in creamy gravy", "hi": "मलाईदार ग्रेवी में धीमी आंच पर पकाई गई काली दाल", "zh": "在奶油肉汁中慢炖的黑扁豆"}, price=16.00, sort_order=3),
    MenuItem(category_id=mains.id, name={"en": "Chicken Biryani", "hi": "चिकन बिरयानी", "zh": "鸡肉香饭"}, description={"en": "Fragrant basmati rice layered with spiced chicken", "hi": "मसालेदार चिकन के साथ परतदार सुगंधित बासमती चावल", "zh": "香米与五香鸡肉分层烹制"}, price=20.00, sort_order=4),
    MenuItem(category_id=breads.id, name={"en": "Garlic Naan", "hi": "गार्लिक नान", "zh": "蒜香烤饼"}, description={"en": "Leavened bread topped with garlic and butter", "hi": "लहसुन और मक्खन के साथ नान", "zh": "发酵面饼配以大蒜和黄油"}, price=4.50, sort_order=1),
    MenuItem(category_id=breads.id, name={"en": "Roti", "hi": "रोटी", "zh": "全麦烤饼"}, description={"en": "Whole wheat flat bread", "hi": "साबुत गेहूं की रोटी", "zh": "全麦薄饼"}, price=3.00, sort_order=2),
    MenuItem(category_id=breads.id, name={"en": "Cheese Naan", "hi": "चीज़ नान", "zh": "奶酪烤饼"}, description={"en": "Naan stuffed with melted cheese", "hi": "पिघले हुए पनीर से भरा नान", "zh": "夹心融化奶酪的烤饼"}, price=5.50, sort_order=3),
    MenuItem(category_id=desserts.id, name={"en": "Gulab Jamun (2 pcs)", "hi": "गुलाब जामुन (2 टुकड़े)", "zh": "玫瑰奶球 (2个)"}, description={"en": "Deep-fried milk dumplings in rose syrup", "hi": "गुलाब सिरप में डूबे हुए दूध के गोले", "zh": "油炸牛奶团浸泡在玫瑰糖浆中"}, price=7.00, sort_order=1),
    MenuItem(category_id=desserts.id, name={"en": "Mango Lassi", "hi": "मैंगो लस्सी", "zh": "芒果酸奶饮"}, description={"en": "Chilled yogurt drink with mango pulp", "hi": "आम के गूदे के साथ ठंडा दही पेय", "zh": "芒果果肉与冰镇酸奶调制"}, price=6.00, sort_order=2),
    MenuItem(category_id=drinks.id, name={"en": "Masala Chai", "hi": "मसाला चाय", "zh": "印度香料茶"}, description={"en": "Spiced Indian tea with milk", "hi": "दूध के साथ मसालेदार भारतीय चाय", "zh": "加香料的印度奶茶"}, price=4.00, sort_order=1),
    MenuItem(category_id=drinks.id, name={"en": "Soft Drink", "hi": "सॉफ्ट ड्रिंक", "zh": "汽水"}, description={"en": "Coke, Sprite, Fanta", "hi": "कोक, स्प्राइट, फ़ैंटा", "zh": "可口可乐、雪碧、芬达"}, price=3.50, sort_order=2),
    MenuItem(category_id=drinks.id, name={"en": "Mango Lassi", "hi": "मैंगो लस्सी", "zh": "芒果酸奶饮"}, description={"en": "Creamy yogurt mango shake", "hi": "मलाईदार दही आम शेक", "zh": "奶油芒果酸奶昔"}, price=6.00, sort_order=3),
]
db.add_all(items)
db.flush()

# Add spice level modifier to mains
butter_chicken = items[3]
spice_group = ModifierGroup(menu_item_id=butter_chicken.id, name={"en": "Spice Level", "hi": "मसाला स्तर", "zh": "辣度"}, type="single", is_required=True)
db.add(spice_group)
db.flush()
db.add_all([
    ModifierOption(group_id=spice_group.id, name={"en": "Mild", "hi": "हल्का", "zh": "微辣"}, price_modifier=0),
    ModifierOption(group_id=spice_group.id, name={"en": "Medium", "hi": "मध्यम", "zh": "中辣"}, price_modifier=0),
    ModifierOption(group_id=spice_group.id, name={"en": "Hot", "hi": "तीखा", "zh": "特辣"}, price_modifier=0),
])

db.commit()
db.close()
print(f"Seeded '{restaurant.name}' with 12 tables and {len(items)} menu items across 5 categories.")
print(f"Staff dashboard: http://localhost:8000/tandoori-flame/staff/login (password: dineflow123)")
print(f"Super admin:     http://localhost:8000/super-admin/login (password: admin123)")
print(f"Customer menu:   http://localhost:8000/tandoori-flame/menu/<table-token>")
print(f"(check /super-admin/restaurant/1/tables for QR tokens)")
