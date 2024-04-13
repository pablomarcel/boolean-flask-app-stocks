import os
import io
import zipfile
import logging
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from waitress import serve
import matplotlib.pyplot as plt
import yfinance as yf

# Set default style for the plots to better fit the dark theme
plt.rcParams.update({
    'figure.facecolor': '#353535',
    'axes.facecolor': '#353535',
    'axes.edgecolor': 'white',
    'axes.labelcolor': 'white',
    'text.color': 'white',
    'xtick.color': 'white',
    'ytick.color': 'white',
    'grid.color': 'white',
    'grid.alpha': 0.3,
    'lines.color': '#ffc801',
    'lines.markersize': 8,  # Adjust this if needed
})

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# app.config[
#     "JWT_SECRET_KEY"
# ] = "2465344b2907b5222e969f35ef907e5c24923623d673996eaad9faa710ab2016"

app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY")

jwt = JWTManager(app)


@app.route("/plot_stock", methods=["POST"])
@jwt_required()
def plot_stock():
    try:
        # Extract the stock ticker from the request
        data = request.json
        ticker = data["ticker"]
        logger.info(f"Received request to plot data for ticker: {ticker}")

        # Download stock data
        start_date = "2023-04-11"
        end_date = "2024-04-11"
        stock_data = yf.download(ticker, start=start_date, end=end_date)

        # Create a Zip file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Market Cap Plot
            with io.BytesIO() as market_cap_buffer:
                plt.figure()
                stock_data["MarketCap"] = stock_data["Open"] * stock_data["Volume"]
                stock_data["MarketCap"].plot(
                    title=f"{ticker} Market Cap", figsize=(10, 5), color='#ffc801'
                )
                plt.savefig(market_cap_buffer, format="png")
                plt.close()
                market_cap_buffer.seek(0)
                zip_file.writestr("market_cap.png", market_cap_buffer.getvalue())

            # Moving Average Plot
            with io.BytesIO() as moving_average_buffer:
                plt.figure()
                stock_data["MA50"] = stock_data["Open"].rolling(50).mean()
                stock_data["MA200"] = stock_data["Open"].rolling(200).mean()
                stock_data["MA50"].plot(label="MA50", color='#ffc801')
                stock_data["MA200"].plot(label="MA200", color='#00ff00')
                plt.title(f"{ticker} Moving Averages")
                plt.legend()
                plt.savefig(moving_average_buffer, format="png")
                plt.close()
                moving_average_buffer.seek(0)
                zip_file.writestr(
                    "moving_average.png", moving_average_buffer.getvalue()
                )

            # Volatility Plot
            with io.BytesIO() as volatility_buffer:
                plt.figure()
                stock_data["returns"] = (
                    stock_data["Close"] / stock_data["Close"].shift(1)
                ) - 1
                stock_data["returns"].hist(bins=100, alpha=0.75, figsize=(10, 5), color='#ffc801')
                plt.title(f"{ticker} Volatility")
                plt.savefig(volatility_buffer, format="png")
                plt.close()
                volatility_buffer.seek(0)
                zip_file.writestr("volatility.png", volatility_buffer.getvalue())

        zip_buffer.seek(0)

        return send_file(
            zip_buffer,
            attachment_filename=f"{ticker}_plots.zip",
            as_attachment=True,
            mimetype="application/zip",
        )

    except Exception as e:
        logger.error(f"Error generating plots for {ticker}: {e}")
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=8080)
