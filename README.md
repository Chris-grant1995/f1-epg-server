# F1 EPG Server

A Flask-based web server that provides the current Formula 1 schedule in XMLTV format, suitable for Electronic Program Guides (EPG). It fetches data from the Jolpica API, includes all practice, qualifying, sprint, and race sessions, and generates informative placeholder entries between sessions. The output can be customized to a specific timezone.

## Features

*   Fetches the current Formula 1 season schedule.
*   Generates EPG data in standard XMLTV format.
*   Includes all sessions: First Practice, Second Practice, Third Practice, Qualifying, Sprint Qualifying, Sprint Race, and the Main Race.
*   Adds intelligent placeholder entries between sessions, indicating the next upcoming session and its local time.
*   Supports timezone customization for EPG output via a command-line argument.
*   Dockerized for easy deployment.

## Technologies Used

*   **Python 3.x**
*   **Flask:** Web framework for the server.
*   **requests:** For making HTTP requests to the F1 API.
*   **pytz:** For robust timezone handling.
*   **xml.etree.ElementTree:** For XML generation.
*   **Docker:** For containerization.

## Setup (Local Development)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Chris-grant1995/f1-epg-server.git
    cd f1-epg-server
    ```

2.  **Create and activate a Python virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage (Local Server)

To run the server, you can specify the port and the desired timezone. If no timezone is provided, it defaults to UTC.

```bash
python3 app.py --port 5001 --timezone Europe/London
```

Replace `Europe/London` with your desired timezone (e.g., `America/New_York`, `Asia/Tokyo`).

Once the server is running, access the EPG XML at: `http://127.0.0.1:5001/epg.xml`

## Docker Usage

### Build the Docker Image

Navigate to the project root directory (where `Dockerfile` is located) and run:

```bash
docker build -t f1-epg-server .
```

### Run the Docker Container

You can run the Docker container, mapping the internal port 5001 to an external port (e.g., 8000) and specifying the timezone:

```bash
docker run -p 8000:5001 --name f1-epg-app f1-epg-server python app.py --port 5001 --timezone Europe/London
```

Access the EPG XML at: `http://127.0.0.1:8000/epg.xml`

To stop the container:

```bash
docker stop f1-epg-app
docker rm f1-epg-app
```

## API Source

This project uses the [Jolpica API](https://api.jolpi.ca/ergast/f1/2025.json) for Formula 1 schedule data.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details (Note: A `LICENSE` file is not included in this repository yet, but it's good practice to add one).

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.
