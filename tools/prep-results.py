#!/usr/bin/env python3
"""
מכין צילומי מסך של תיוגים/נתוני מעורבות לקיר התוצאות באתר.

מה הוא עושה:
  1. חותך את שורת הסטטוס למעלה (שעה, סוללה, קליטה) ואת סרגל הפעולות למטה
     ("Send a thought", Activity/Facebook/Share) — בזיהוי אוטומטי לפי פסים
     אחידים בקצוות, עם נפילה לאחוזים קבועים אם הזיהוי לא בטוח.
  2. מקטין לרוחב סביר לאתר ושומר כ-JPEG מותאם.

שימוש:
  python3 tools/prep-results.py <תיקיית-מקור> [--top 6] [--bottom 11] [--dry]

--top/--bottom הם אחוזים, ומשמשים רק כשהזיהוי האוטומטי נכשל או כשכופים אותם.
"""
import sys, os, argparse
from PIL import Image

MAX_W = 900          # רוחב יעד — הכרטיסים באתר לא עולים על ~410px, אז זה עם מרווח ל-retina
JPEG_Q = 86

def uniform_rows(img, from_top=True, max_scan_frac=0.22, tol=10):
    """מוצא כמה שורות רצופות מהקצה הן 'פס אחיד' (שורת סטטוס/סרגל).
    מחזיר מספר פיקסלים לחיתוך, או 0 אם לא נמצא גבול ברור."""
    w, h = img.size
    px = img.convert('RGB').load()
    scan = int(h * max_scan_frac)
    step = max(1, w // 40)                      # דגימה ולא כל פיקסל — מספיק ומהיר
    rng = range(scan) if from_top else range(h - 1, h - scan - 1, -1)

    def row_avg(y):
        s = [0, 0, 0]; n = 0
        for x in range(0, w, step):
            r, g, b = px[x, y][:3]; s[0] += r; s[1] += g; s[2] += b; n += 1
        return (s[0] / n, s[1] / n, s[2] / n)

    base = row_avg(rng[0])
    last = 0
    for i, y in enumerate(rng):
        a = row_avg(y)
        if max(abs(a[j] - base[j]) for j in range(3)) > tol:
            break
        last = i
    # גבול אמין רק אם הפס בעל עובי סביר (לא 2 פיקסלים ולא כל התמונה)
    return last if 8 <= last <= scan * 0.95 else 0

def process(src, dst, top_pct, bot_pct, force, dry):
    img = Image.open(src)
    if img.mode in ('RGBA', 'P', 'LA'):
        img = img.convert('RGB')
    w, h = img.size

    top = int(h * top_pct / 100) if force else (uniform_rows(img, True)  or int(h * top_pct / 100))
    bot = int(h * bot_pct / 100) if force else (uniform_rows(img, False) or int(h * bot_pct / 100))

    if top + bot >= h * 0.6:                    # הגנה: לעולם לא לחתוך יותר מ-60%
        top = int(h * top_pct / 100); bot = int(h * bot_pct / 100)

    out = img.crop((0, top, w, h - bot))
    if out.width > MAX_W:
        out = out.resize((MAX_W, round(out.height * MAX_W / out.width)), Image.LANCZOS)

    print(f"  {os.path.basename(src):<42} {w}x{h} → {out.width}x{out.height}  "
          f"(חתך {top}px למעלה, {bot}px למטה)")
    if not dry:
        out.save(dst, 'JPEG', quality=JPEG_Q, optimize=True, progressive=True)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('src')
    p.add_argument('--top', type=float, default=6)
    p.add_argument('--bottom', type=float, default=11)
    p.add_argument('--force', action='store_true', help='לכפות את האחוזים במקום זיהוי אוטומטי')
    p.add_argument('--dry', action='store_true', help='רק להדפיס, בלי לכתוב')
    a = p.parse_args()

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outdir = os.path.join(here, 'images', 'results')
    os.makedirs(outdir, exist_ok=True)

    files = sorted(f for f in os.listdir(a.src)
                   if f.lower().endswith(('.png', '.jpg', '.jpeg', '.heic')))
    if not files:
        print('לא נמצאו תמונות בתיקייה:', a.src); return 1

    print(f'{len(files)} תמונות → {outdir}\n')
    for i, f in enumerate(files, 1):
        stem = f'shot-{i:02d}.jpg'
        try:
            process(os.path.join(a.src, f), os.path.join(outdir, stem),
                    a.top, a.bottom, a.force, a.dry)
        except Exception as e:
            print(f'  ✗ {f}: {e}')
    print('\nסיום. עכשיו להוסיף את שמות הקבצים למערך shots ב-index.html.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
