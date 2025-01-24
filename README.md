# CryptoCurrency Price Tracker

This project is a cryptocurrency price tracker that provides real-time updates on the prices of various cryptocurrencies. It is built using Flask, Tailwind CSS, and several other libraries.

## Technologies Used

- **Python**: v3.9.12.
- **Flask**: A micro web framework for Python.
- **Flask-SocketIO**: Enables real-time communication between the client and server.
- **Flask-WebSocket-Client**: A WebSocket client for Flask.
- **Eventlet**: A concurrent networking library for Python.
- **Requests**: A simple HTTP library for Python.
- **Binance API**: Used to fetch cryptocurrency prices.
- **CoinMarketCap API**: Used to fetch additional cryptocurrency data.
- **Tailwind CSS**: A utility-first CSS framework for styling the frontend.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/CryptoCurrency-Price-Tracker.git
    cd CryptoCurrency-Price-Tracker
    ```

2. Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

4. Set up environment variables:
    ```bash
    export COINMARKETCAP_API_KEY='your_coinmarketcap_api_key'
    ```

## Running the Application

1. Start the Flask application:
    ```bash
    flask run
    ```

2. Open your web browser and navigate to `http://127.0.0.1:5000` to view the application.

## Usage

- The application will display real-time prices of various cryptocurrencies.
- You can add or remove cryptocurrencies to track using the provided interface.

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Commit your changes (`git commit -am 'Add new feature'`).
5. Push to the branch (`git push origin feature-branch`).
6. Create a new Pull Request.

## Docker

To run the application using Docker, follow these steps:

1. Build the Docker image:
    ```bash
    docker build -t my-flask-app .
    ```

2. Run the Docker container:
    ```bash
    docker run -p 5000:5000 my-flask-app
    ```

Open your web browser and navigate to `http://localhost:5000/` to view the application.



Optional : 

3. THis is my container ID is:
    ```bash
    Container Id : 302cf206e7a2d52f825a4572c5998585d1df2fe94c6b172b13d811bfaa4c31a9
    ```
