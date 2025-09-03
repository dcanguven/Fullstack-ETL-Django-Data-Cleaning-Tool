import json
import os
from pathlib import Path
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from .pipeline import run_pipeline
import pandas as pd

DEFAULT_KEEP = ["record_id","date","description","address","contractor_owner","valuation","fees"]

def _cfg_path(name):
    return settings.CONFIG_DIR / name

def _load_json(name, fallback):
    p = _cfg_path(name)
    if not p.exists():
        p.write_text(json.dumps(fallback, ensure_ascii=False, indent=2), encoding="utf-8")
    return json.loads(p.read_text(encoding="utf-8"))

def _save_json(name, data):
    _cfg_path(name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def upload_view(request):
    if request.method == "POST":
        fs = FileSystemStorage(location=settings.UPLOAD_DIR)
        f = request.FILES["file"]

        # Orijinal istemci dosya adı (gösterim için)
        original_name = Path(f.name).name

        # Diskte saklanan ad (çakışma önleme için değişebilir)
        stored_name = fs.save(original_name, f)

        full_path = settings.UPLOAD_DIR / stored_name
        request.session["uploaded_file"] = str(full_path)        # disk yolu (stored)
        request.session["stored_name"] = stored_name             # diskteki gerçek ad
        request.session["original_name"] = original_name         # kullanıcıya göstereceğimiz ad

        return redirect("preview")
    return render(request, "etl/upload.html")

def preview_view(request):
    path = request.session.get("uploaded_file")
    if not path:
        return redirect("upload")

    p = Path(path)
    # İlk 20 satır
    if str(p).lower().endswith(".csv"):
        df = pd.read_csv(p, nrows=20)
    else:
        df = pd.read_excel(p, nrows=20)

    table = df.to_html(index=False)

    # EKRANDA ORİJİNAL ADI GÖSTER
    filename = request.session.get("original_name", Path(path).name)

    return render(request, "etl/preview.html", {
        "table": table,
        "filename": filename
    })

def mapping_view(request):
    data = _load_json("header_map.json", {})
    if request.method == "POST":
        txt = request.POST.get("json_text", "")
        _save_json("header_map.json", json.loads(txt))
        return redirect("rules")
    return render(request, "etl/mapping.html", {"json_text": json.dumps(data, ensure_ascii=False, indent=2)})

def rules_view(request):
    data = _load_json("classification_rules.json", {
        "search_fields":["description","address"],
        "priority":["Residential","Commercial"],
        "rules":{"Residential":["residential","house","home"],"Commercial":["commercial","office","retail"]}
    })
    if request.method == "POST":
        txt = request.POST.get("json_text", "")
        _save_json("classification_rules.json", json.loads(txt))
        return redirect("process")
    return render(request, "etl/rules.html", {"json_text": json.dumps(data, ensure_ascii=False, indent=2)})

def process_view(request):
    path = request.session.get("uploaded_file")
    if not path:
        return redirect("upload")

    if request.method == "POST":
        header_map = _load_json("header_map.json", {})
        rules = _load_json("classification_rules.json", {})

        # Orijinal ada göre kullanıcı-dostu çıktı adı: input_std.csv
        original_name = request.session.get("original_name", Path(path).name)
        stem, ext = os.path.splitext(original_name)
        # Pipeline CSV üretiyor; uzantı yoksa .csv ekleyelim
        out_display_name = f"{stem}_std{ext if ext else '.csv'}"

        # Diskte kaydederken de aynı ismi kullan (çakışma ihtimali varsa storage yine değiştirebilir)
        out_path = settings.OUTPUT_DIR / out_display_name

        df = run_pipeline(path, out_path, header_map, rules, DEFAULT_KEEP)

        request.session["output_file"] = str(out_path)
        request.session["output_display_name"] = out_display_name  # EKRANDA bunu göster

        stats = {
            "rows": int(df.shape[0]),
            "cols": int(df.shape[1]),
            "unknown": int((df["classification"]=="Unknown").sum()) if "classification" in df.columns else 0
        }
        request.session["stats"] = stats
        return redirect("done")

    return render(request, "etl/process.html")

def done_view(request):
    out_path = request.session.get("output_file")
    in_path = request.session.get("uploaded_file")
    stats = request.session.get("stats", {})
    if not out_path or not in_path:
        return redirect("upload")

    in_p = Path(in_path)
    out_p = Path(out_path)

    # ORIGINAL ve PROCESSED için 10'ar satır örnek
    if str(in_p).lower().endswith(".csv"):
        df_src = pd.read_csv(in_p, nrows=10)
    else:
        df_src = pd.read_excel(in_p, nrows=10)
    preview_table_src = df_src.to_html(index=False)

    if str(out_p).lower().endswith(".csv"):
        df_out = pd.read_csv(out_p, nrows=10)
    else:
        df_out = pd.read_excel(out_p, nrows=10)
    preview_table_out = df_out.to_html(index=False)

    # İndirme URL'si
    url = settings.MEDIA_URL + "outputs/" + out_p.name

    # EKRANDA ORİJİNAL ADI GÖSTER (input.csv), PROCESSED İÇİN DE KULLANICI-DOSTU AD
    src_filename = request.session.get("original_name", in_p.name)
    out_filename = request.session.get("output_display_name", out_p.name)

    return render(request, "etl/done.html", {
        "url": url,
        "stats": stats,
        "src_filename": src_filename,
        "out_filename": out_filename,
        "preview_table_src": preview_table_src,
        "preview_table_out": preview_table_out
    })