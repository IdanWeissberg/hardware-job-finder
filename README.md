# 🔧 Hardware Job Monitor — מוניטור משרות חומרה

מערכת אוטומטית שסורקת את דפי הקריירה של חברות טכנולוגיה מובילות **כל 4 שעות** ושולחת התראות ל-WhatsApp כשמתפרסמת **משרת חומרה חדשה המיועדת לסטודנטים/מתמחים**.

---

## תוכן עניינים
1. [דרישות מוקדמות](#דרישות-מוקדמות)
2. [הגדרה ראשונית — CallMeBot](#הגדרה-ראשונית--callmebot)
3. [יצירת ה-Secrets ב-GitHub](#יצירת-ה-secrets-ב-github)
4. [הפעלה ראשונה — יצירת Baseline](#הפעלה-ראשונה--יצירת-baseline)
5. [הוספת חברה חדשה](#הוספת-חברה-חדשה)
6. [הסרת חברה מהניטור](#הסרת-חברה-מהניטור)
7. [שינוי מילות החיפוש](#שינוי-מילות-החיפוש)
8. [שעות שקט](#שעות-שקט)
9. [הפעלה ידנית](#הפעלה-ידנית)
10. [מבנה הקוד](#מבנה-הקוד)

---

## דרישות מוקדמות

- חשבון GitHub
- מספר WhatsApp פעיל (כדי לקבל התראות)
- Python 3.11+ (לריצה מקומית בלבד — ב-GitHub Actions הכל אוטומטי)

---

## הגדרה ראשונית — Telegram (מומלץ)

המערכת שולחת התראות דרך **Telegram** — חינמי, מיידי, ואמין (ללא מגבלות תפוסה כמו ב-CallMeBot).

### שלב 1: יצירת בוט

1. ב-Telegram חפשו את **@BotFather** ופתחו צ'אט.
2. שלחו `/newbot`, בחרו שם ושם-משתמש שמסתיים ב-`bot`.
3. תקבלו **טוקן** במבנה `8123456789:AAH...xyz` — שמרו אותו.
4. פתחו את הבוט החדש שיצרתם ושלחו לו הודעה כלשהי (למשל `hi`).

### שלב 2: השגת ה-Chat ID

1. חפשו את **@userinfobot** ב-Telegram ולחצו **Start**.
2. הוא יחזיר שורה כמו `Id: 123456789` — זהו ה-Chat ID שלכם.

> **חלופה (אופציונלי):** המערכת תומכת גם ב-CallMeBot (WhatsApp) וב-Twilio.
> ל-CallMeBot: שלחו `I allow callmebot to send me messages` למספר הבוט הרשמי,
> והגדירו `CALLMEBOT_PHONE` + `CALLMEBOT_API_KEY` במקום משתני ה-Telegram.

---

## יצירת ה-Secrets ב-GitHub

ה-Secrets הם משתני סביבה מוצפנים שה-GitHub Actions משתמש בהם. **לעולם אל תכתבו אותם בקוד!**

### איך להוסיף Secrets:

1. עברו לדף הריפו ב-GitHub
2. לחצו על **Settings** → **Secrets and variables** → **Actions**
3. לחצו על **New repository secret** עבור כל אחד מהמשתנים הבאים:

| שם ה-Secret | תיאור | דוגמה |
|-------------|--------|--------|
| `WHATSAPP_PROVIDER` | ספק ההתראות | `telegram` |
| `TELEGRAM_BOT_TOKEN` | הטוקן שקיבלתם מ-@BotFather | `8123456789:AAH...` |
| `TELEGRAM_CHAT_ID` | ה-Chat ID שלכם מ-@userinfobot | `123456789` |

> **אם אתם משתמשים ב-CallMeBot (WhatsApp) במקום**, הגדירו:
> - `WHATSAPP_PROVIDER` = `callmebot`
> - `CALLMEBOT_PHONE` = `+972501234567`
> - `CALLMEBOT_API_KEY` = `1234567`

> **אם אתם משתמשים ב-Twilio (אופציונלי)**, הוסיפו גם:
> - `WHATSAPP_PROVIDER` = `twilio`
> - `TWILIO_ACCOUNT_SID`
> - `TWILIO_AUTH_TOKEN`
> - `TWILIO_FROM` = `whatsapp:+14155238886`
> - `TWILIO_TO` = `whatsapp:+972501234567`

---

## הפעלה ראשונה — יצירת Baseline

בהפעלה הראשונה, המערכת תאתר מאות משרות קיימות. אם לא מגדירים Baseline, תקבלו הצפה של התראות על משרות ישנות.

### איך להריץ Baseline:

1. עברו ל-**Actions** בדף ה-GitHub שלכם
2. בחרו את ה-workflow **"Hardware Job Monitor"**
3. לחצו על **Run workflow**
4. סמנו את ✅ **"Run in --init mode"**
5. לחצו **Run workflow**

המערכת תסרוק את כל החברות ותשמור את כל המשרות הקיימות כ"כבר נראו" — מבלי לשלוח אליכם כלום. מעכשיו תקבלו התראות רק על משרות **חדשות**.

---

## הוספת חברה חדשה

פתחו את הקובץ `config.yaml` והוסיפו ערך חדש תחת `companies:`.

### דוגמה — חברה שמשתמשת ב-Greenhouse:
```yaml
- name: "חברה חדשה"
  enabled: true
  ats: greenhouse
  board: "company-token-here"    # מופיע ב-URL של דף הקריירה ב-Greenhouse
  location_filter: "Israel"
```

### דוגמה — חברה שמשתמשת ב-Lever:
```yaml
- name: "חברה חדשה"
  enabled: true
  ats: lever
  company: "company-slug"        # מופיע ב-URL: jobs.eu.lever.co/company-slug
```

### דוגמה — חברה שמשתמשת ב-Comeet:
```yaml
- name: "חברה חדשה"
  enabled: true
  ats: comeet
  slug: "company-slug"           # מופיע ב-URL: comeet.com/jobs/company-slug
```

### דוגמה — חברה עם דף קריירה רגיל (scraper):
```yaml
- name: "חברה חדשה"
  enabled: true
  ats: scraper
  careers_url: "https://example.com/careers"
  fragile: true                  # מסמן שה-scraper עלול להישבר אם האתר ישתנה
```

### איך לזהות את פלטפורמת ה-ATS של חברה?

1. גשו לדף הקריירה של החברה
2. פתחו DevTools → Network → XHR/Fetch
3. חפשו בקשות ל:
   - `greenhouse.io` → ats: `greenhouse`, board: `<token מה-URL>`
   - `lever.co` / `lever.eu` → ats: `lever`, company: `<slug מה-URL>`
   - `comeet.co` / `comeet.com/jobs` → ats: `comeet`, slug: `<slug מה-URL>`
   - `myworkdayjobs.com` → ats: `workday`
   - `smartrecruiters.com` → ats: `smartrecruiters`
   - `icims.com` → ats: `icims`
   - `eightfold.ai` → ats: `eightfold`
   - `workable.com` → ats: `workable`

---

## הסרת חברה מהניטור

ב-`config.yaml`, שנו את `enabled: true` ל-`enabled: false`:
```yaml
- name: "חברה שלא רוצים לנטר"
  enabled: false    # ← שנו לכאן
  ...
```

---

## שינוי מילות החיפוש

ב-`config.yaml`, תחת `keywords:`, ניתן להוסיף/להסיר מילות מפתח:

```yaml
keywords:
  hardware:        # משרה חייבת להכיל לפחות מילה אחת מכאן
    - hardware
    - asic
    - fpga
    # הוסיפו מילים לפי הצורך

  student:         # וגם לפחות מילה אחת מכאן
    - intern
    - student
    # הוסיפו מילים לפי הצורך
```

---

## שעות שקט

ב-`config.yaml`, ניתן לשנות את שעות השקט:
```yaml
quiet_hours:
  start: "00:00"
  end: "07:00"
  timezone: "Asia/Jerusalem"
```

בין השעות `00:00` ל-`07:00` (שעון ישראל):
- משרות חדשות **מתגלות ונשמרות** כ"כבר נראו" (לא יתגלו שוב)
- ההתראות **מצטברות בתור** (`pending_notifications.json`)
- ב-**07:00 הראשון** מתבצע שליחת דיג'סט בודד עם כל הממצאים, ואז התור מתנקה

---

## הפעלה ידנית

1. עברו ל-**Actions** ב-GitHub
2. בחרו **"Hardware Job Monitor"**
3. לחצו **Run workflow**

ניתן לבחור:
- **ריצה רגילה** (ברירת מחדל) — בדיקת משרות חדשות ושליחת התראות
- **Init mode** — יצירת Baseline ללא התראות
- **Test notify** — שליחת הודעת בדיקה ל-WhatsApp לאימות ה-Secrets

---

## מבנה הקוד

```
.
├── config.yaml                  # 📋 הגדרות — חברות + מילות מפתח
├── main.py                      # 🏃 נקודת כניסה ראשית
├── filter.py                    # 🔍 פילטר רלוונטיות
├── state.py                     # 💾 ניהול סטייט (seen_jobs / pending)
├── notifier.py                  # 📱 שליחת WhatsApp
├── requirements.txt
├── seen_jobs.json               # 📚 כל המשרות שנראו (מתעדכן אוטומטית)
├── pending_notifications.json   # ⏰ תור ממתין לשעות שקט
├── fetchers/
│   ├── workday.py               # Workday CXS API
│   ├── greenhouse.py            # Greenhouse Job Board API
│   ├── lever.py                 # Lever public postings API
│   ├── comeet.py                # Comeet careers (API + scraper)
│   ├── amazon.py                # Amazon.jobs JSON API
│   ├── apple.py                 # Apple careers POST API
│   ├── microsoft.py             # Microsoft GCS search API
│   ├── smartrecruiters.py       # SmartRecruiters postings API
│   ├── icims.py                 # iCIMS job search
│   ├── google_careers.py        # Google careers scraper
│   ├── eightfold.py             # Eightfold.ai API
│   ├── workable.py              # Workable apply API
│   └── scraper.py               # HTML scraper (fallback)
└── .github/
    └── workflows/
        └── job_monitor.yml      # GitHub Actions workflow
```

---

## פתרון בעיות נפוצות

**לא מקבל הודעות WhatsApp:**
1. בדקו שהרצתם `--init` לפני הריצה הרגילה הראשונה
2. הריצו `Run workflow → Test notify` לאימות ה-Secrets
3. בדקו שהמספר הוזן בפורמט בינלאומי: `+972501234567`

**שגיאה על חברה מסוימת:**
- בדקו ב-Actions logs איזו חברה נכשלה
- ייתכן שה-ATS שינה את ה-URL שלו — עדכנו ב-`config.yaml`
- שגיאות ב-scraper (`fragile: true`) צפויות לפעמים

**הצפה של משרות ישנות:**
- הריצו `--init` שוב (ימחק ויסרוק מחדש)

---

*Built with ❤️ for hardware engineering students in Israel*
