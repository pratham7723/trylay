import os
from flask import Flask, render_template, request, send_file
from layout_engine import generate_layout

app = Flask(__name__)

# The directory containing the bundled images
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    try:
        start_set = int(request.form.get("start_set", 1))
        end_set = int(request.form.get("end_set", 1))
        
        if start_set > end_set:
            start_set, end_set = end_set, start_set

        # Generate the single combined PDF stream
        pdf_stream = generate_layout(start_set, end_set, IMAGES_DIR)
        
        filename = f"layout_sets_{start_set}_to_{end_set}.pdf"
        
        return send_file(
            pdf_stream,
            as_attachment=False,  # This tells the browser to display inline
            download_name=filename,
            mimetype="application/pdf"
        )
    except Exception as e:
        return f"An error occurred: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
