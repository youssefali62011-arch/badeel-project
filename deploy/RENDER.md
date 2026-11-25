# رفع Badeel على Render وربط الدومين

الموقع هيبقى على لينك زي `https://badeel.onrender.com`، وبعدين على الدومين بتاعنا.
فيه الداتا المصرية كاملة (22,757 دوا، والتداخلات، والأمراض، والنشرات)، وموديل البحث جاهز.

**التكلفة:** ‎$7 في الشهر للسيرفر + ‎$0.25 في الشهر للـ Disk (1 جيجا) = **‎$7.25 في الشهر**، والدومين حوالي ‎$11 في السنة.
محتاج كارت فيزا أو ماستركارد مفعّل عليه الشراء أونلاين بالدولار.

الملفات اللي بتعمل الشغل كله:

| الملف | بيعمل إيه |
|---|---|
| `render.yaml` | بيقول لـ Render يعمل إيه: السيرفر، والـ Disk، والإعدادات |
| `deploy/render_start.py` | أول مرة بس: بيحمّل الداتا والموديل ويعمل حساب الأدمن. بعد كده بيعدّي |
| `requirements.txt` | فيه `gunicorn`، السيرفر اللي Render بيشغّل بيه الموقع |

---

## 1. اعمل حساب على Render

1. افتح `https://dashboard.render.com/register`.
2. اختار **GitHub** وادخل بحسابك. كده Render يقدر يشوف الـ repo.
3. أكّد الإيميل.
4. من **Billing** ضيف الكارت. من غيره مش هينفع تختار الخطة المدفوعة.

## 2. اعمل الموقع من الـ Blueprint

1. في Render، من فوق: **New ← Blueprint**.
2. اختار الـ repo **badeel-project**. لو مش ظاهر، دوس **Configure GitHub** واديله صلاحية عليه.
3. Render هيقرا `render.yaml` ويوريك: Web service اسمه **badeel**، وDisk اسمه **badeel-data**.
4. هيطلب منك قيمتين، دول اللي هتدخل بيهم كأدمن:

| الخانة | اكتب فيها |
|---|---|
| `BADEEL_ADMIN_EMAIL` | إيميل الأدمن، مثلًا إيميلك |
| `BADEEL_ADMIN_PASSWORD` | 15 حرف على الأقل، ومايكونش فيه كلمة admin ولا إيميلك. جملة زي `koshary fel kolya ya gama3a` |

5. دوس **Apply** (أو **Deploy Blueprint**).

## 3. استنى أول تشغيل (حوالي 5 دقايق)

افتح الـ service **badeel** وبعدين **Logs**. هتشوف بالترتيب:

```
+ manage.py import-csv data/egypt/egyptian-drugs.csv --replace
Added 22757, updated 5, skipped 2308.
+ manage.py import-enrichment dataset
Loaded 72,490 interactions, 32,291 disease rows and 1,007 leaflets from dataset.
+ manage.py install-model deploy/search_model.json
Search model installed (1500 drugs, ...).
+ manage.py create-admin --email ... --name Admin
Admin account created.
Badeel is ready.
... Listening at: http://0.0.0.0:10000
```

لما يبقى مكتوب فوق **Live** باللون الأخضر، دوس على اللينك اللي تحت اسم الـ service
(`https://badeel-xxxx.onrender.com`). **ده أول تسليم.**

ادخل بالإيميل والباسورد اللي كتبتهم. أول بحث بعد كل تشغيل بياخد حوالي 4 ثواني، لأن الموقع بيجهز البحث، وبعدها بيبقى سريع.

## 4. الدومين (بعد ما الفريق يتفق على الاسم)

### اشتريه من Cloudflare

1. اعمل حساب على `https://dash.cloudflare.com/sign-up`.
2. من القايمة: **Domain Registration ← Register Domains**، ودوّر على الاسم.
3. اشتريه بالكارت (حوالي ‎$11 في السنة، ونفس السعر في التجديد).

### اربطه بـ Render

1. في Render: الـ service **badeel** ← **Settings** ← **Custom Domains** ← **Add Custom Domain**.
2. اكتب الدومين من غير www، مثلًا `badeel-eg.com`، و**Save**. Render هيضيف `www` لوحده.
3. في Cloudflare: افتح الدومين.
   - **SSL/TLS ← Overview**: اختار **Full**.
   - **DNS ← Records**: امسح أي سجل نوعه **AAAA**، وبعدين ضيف سجلين:

| Type | Name | Target | Proxy status |
|---|---|---|---|
| CNAME | `@` | لينك Render من غير https، مثلًا `badeel-xxxx.onrender.com` | **DNS only** (السحابة رمادي) |
| CNAME | `www` | نفس اللينك | **DNS only** (السحابة رمادي) |

4. ارجع لـ Render ← **Custom Domains** ← دوس **Verify** جنب الدومين.
   بعد دقايق هيبقى عليه علامة خضرا، والـ HTTPS بيتعمل لوحده.

**خلي السحابة رمادي (DNS only) على طول.** لو خليتها برتقاني، كل الزوار هيبانوا للموقع بعنوان Cloudflare،
وقفل الحسابات بعد المحاولات الغلط هيقفل على الناس كلها مع بعض.

---

## بعد كده

**التحديثات:** أي Pull Request يتعمله **Merge في main** بيتنشر على الموقع لوحده خلال دقايق.
علشان كده جرّب الـ PR على جهازك الأول قبل ما تدمجه.

**الداتا محفوظة:** الحسابات والأدوية المحفوظة وسجل الأمان على الـ Disk، فمش بتتمسح مع التحديثات.
`render_start.py` بيحمّل الداتا **أول مرة بس**.

**لو عايز تبدأ من الأول:** Render ← الـ service ← **Shell**، واكتب:
```bash
rm -rf /var/data/instance
```
وبعدين **Manual Deploy ← Restart service**. الموقع هيحمّل كل حاجة من جديد، وكل الحسابات هتتمسح.

**حسابات تجريبية للعرض:** من نفس الـ **Shell**:
```bash
python manage.py demo-users
```
امسحوها بعد المناقشة، لأن الموقع مفتوح لأي حد معاه اللينك.

**علشان توقف الفلوس:** الـ service ← **Settings** ← **Suspend Web Service**. لو مسحته، الـ Disk والداتا هيتمسحوا.

## حاجات مش هتشتغل على Render

| الحاجة | ليه |
|---|---|
| البحث بصورة العلبة | محتاج برنامج Tesseract، ومش موجود على Render. زرار الكاميرا بيختفي لوحده |
| تذكير الأدوية بالإشعارات وقت ما الموقع مقفول | محتاج Cron Job منفصل بفلوس إضافية. التذكير جوه الموقع (صفحة `/me`) شغال عادي |

## لو حاجة ما اشتغلتش

افتح **Logs** في Render، وانسخ آخر 30 سطر وابعتهم لـ Claude.

| اللي في الـ Logs | الحل |
|---|---|
| `Password rejected` | الباسورد أقل من 15 حرف أو فيه admin أو الإيميل. غيّره من **Environment** واعمل **Manual Deploy** |
| `No admin yet` | ما كتبتش الإيميل أو الباسورد. ضيفهم من **Environment** واعمل **Manual Deploy** |
| `No open ports detected` | التحميل لسه شغال، استنى. لو كمل أكتر من 15 دقيقة ابعت الـ Logs |
