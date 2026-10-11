import os, re, uuid, shutil, subprocess
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)
DOWNLOADS = Path("/tmp/video_downloads")
DOWNLOADS.mkdir(parents=True, exist_ok=True)

@app.get("/")
def index():
    return send_from_directory(".", "index.html")

@app.post("/api/download")
def download():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()
    if not re.match(r"^https?://", url):
        return jsonify(error="URL inválida."), 400
    if not shutil.which("yt-dlp"):
        return jsonify(error="yt-dlp não está disponível no servidor."), 500

    job = uuid.uuid4().hex
    template = str(DOWNLOADS / f"{job}.%(ext)s")
    try:
        subprocess.run(
            ["yt-dlp", "--no-playlist", "--restrict-filenames",
             "-f", "bv*+ba/b", "--merge-output-format", "mp4",
             "-o", template, url],
            check=True, timeout=240, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except subprocess.TimeoutExpired:
        return jsonify(error="O vídeo demorou demais para ser processado."), 504
    except subprocess.CalledProcessError as e:
        return jsonify(error="Não foi possível obter este vídeo. O site pode bloquear o acesso."), 422

    files = list(DOWNLOADS.glob(job + ".*"))
    if not files:
        return jsonify(error="O servidor não gerou o arquivo."), 500
    return jsonify(filename=files[0].name, download_url="/files/" + files[0].name)

@app.get("/files/<path:filename>")
def files(filename):
    return send_from_directory(DOWNLOADS, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
