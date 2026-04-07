# 🤖 Shifo Dorixona Boti - Admin Qo'llanmasi

Ushbu qo'llanma `Shifo Dorixona` telegram botini boshqarish, yangi viloyat, tuman, filial va bo'sh ish o'rinlarini qo'shish yoki o'chirish jarayonlarini tushuntiradi.

---

## 🔑 1. Admin Paneliga Kirish
Administrator sifatida botga kirganingizda, asosiy menyuda **⚙️ Admin panel** tugmasi paydo bo'ladi.  
Bot sizni administrator sifatida tanishi uchun Telegram profilingizning `ID` raqami tizimga kiritilgan bo'lishi kerak.

## 🗂️ 2. Ma'lumotlarni Boshqarish Ierarxiyasi
Botdagi ma'lumotlar quyidagi ketma-ketlikda ishlaydi:
1. **Viloyat** (Masalan: *Toshkent shahri*)
2. **Tuman** (Masalan: *Yunusobod tumani*)
3. **Filial** (Masalan: *Shifa 1-filial*)
4. **Vakansiya / Bo'sh ish o'rni** (Masalan: *Sotuvchi, Provizor*)

⚠️ **Muhim:** Vakansiya yaratishdan oldin uning viloyati, tumani va filiali yaratilgan bo'lishi shart!

---

## ➕ 3. Yangi Ma'lumot Qo'shish

### Viloyat qo'shish:
1. Asosiy menyudan **⚙️ Admin panel** tugmasini bosing. Sizga viloyatlar ro'yxati ochiladi.
2. Eng pastdagi **➕ Add Viloyat** tugmasini bosing.
3. Viloyat nomini kiriting (Masalan: `Samarqand viloyati`).
4. Tasdiqlangandan so'ng viloyat ro'yxatga qo'shiladi.

### Tuman qo'shish:
1. Ro'yxatdan kerakli viloyatni tanlang (ustiga bosing).
2. Yangi menyuda ushbu viloyatning tumanlari ochiladi.
3. **➕ Add Tuman** tugmasini bosing va tuman nomini yozib yuboring.

### Filial qo'shish:
1. Tegishli Tuman nomini tanlang.
2. Ochilgan oynada **➕ Add Filial** tugmasini bosing va filial nomini yozing.

### Vakansiya (bo'sh ish o'rni) qo'shish:
1. Tegishli Filial nomini tanlang.
2. Filtrdan so'ng, **➕ Add Vakansiya** tugmasini bosing va lavozim nomini (masalan: `Sotuvchi`) yoshizb yuboring.

*Eslatma: Qo'shish jarayonida xato qilib yuborsangiz, `❌ Cancel` (Bekor qilish) tugmasi orqali to'xtatishingiz mumkin.*

---

## 🗑️ 4. Ma'lumotlarni O'chirish
Agar biror filial yopilsa yoki vakansiyaga xodim topilsa, uni o'chirib tashlash mumkin.

1. O'chirmoqchi bo'lgan ma'lumotingiz turadigan menyuga kirasiz.
2. Masalan, bitta vakansiyani o'chirmoqchisiz: *Viloyat -> Tuman -> Filial* ichiga kirasiz.
3. Ostki qismdagi **❌ Delete Vakansiya** tugmasini bosasiz.
4. Bot sizga o'chirish uchun o'sha filialdagi mavjud barcha vakansiyalarni savatcha (`🗑`) belgisi bilan ko'rsatadi.
5. O'chirmoqchi bo'lganingiz ustiga bossangiz, u tizimdan o'chiriladi.

⚠️ **DIQQAT:** Agar siz qaysidir viloyat yoki tumanni o'chirsangiz, **unga tegishli bo'lgan barcha filiallar va ularning ichidagi barcha vakansiyalar ham avtomatik o'chib ketadi**. Shuning uchun ehtiyotkorlik bilan o'chiring.

---

## 📩 5. Arizalarni (Zayavkalarni) Qabul Qilish
Oddiy foydalanuvchi "Ariza qoldirish" orqali so'rovnomani to'ldirganda (Ismi, manzili, tajribasi, telefon raqami va hokazo), bot avtomatik tarzda barcha administratorlarga bitta yig'ma **"📩 YANGI ARIZA TUSHDI"** xabarini yuboradi.  
Xabarda nomzodning barcha javoblari va ushbu nomzod qaysi filialdagi lavozimni qidirayotgani aniq ko'rsatilgan bo'ladi. 

Siz ko'rsatilgan Telegram `@username` yoki telefon raqami orqali u bilan mustaqil aloqaga chiqishingiz mumkin. Menyu orqali ariza holatini o'zgartirish (qabul qilindi/qaytarildi) funksiyalari hozircha tizimda mavjud emas, jarayon to'g'ridan-to'g'ri bog'lanish orqali hal qilinadi.

---
**Qo'shimcha tugmalar:**
- **⬅️ Back (Orqaga):** Bir qadam ortga qaytish.
- **🏠 Main Menu (Asosiy menyu):** To'g'ridan-to'g'ri dastlabki holatga qaytish.

*Shifo Dorixona Boti barcha ishlarida muvaffaqiyatlar tilaymiz!*
