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

The Docker image for this application is available on GitHub Container Registry.

### Pull the Docker Image

```bash
docker pull ghcr.io/chris-grant1995/f1-epg-server:latest
```

### Run the Docker Container

You can run the Docker container, mapping the internal port 5001 to an external port (e.g., 8000) and specifying the timezone:

```bash
docker run -p 8000:5001 --name f1-epg-app ghcr.io/chris-grant1995/f1-epg-server:latest python app.py --port 5001 --timezone Europe/London
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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Docker Compose Usage

Docker Compose allows you to define and run multi-container Docker applications. For this project, it simplifies running the F1 EPG server.

1.  **Build and Run with Docker Compose:**
    Navigate to the project root directory (where `docker-compose.yml` is located) and run:
    ```bash
    docker compose up -d
    ```
    This command pulls the Docker image (if not already available locally), starts the container in detached mode (`-d`), and maps port 5001 (as defined in `docker-compose.yml`). The timezone is set to `Europe/London` by default in the `docker-compose.yml`, but you can override it by setting the `TZ` environment variable before running `docker compose up`.

    Example to run with a different timezone:
    ```bash
    TZ=America/New_York docker compose up -d
    ```

2.  **Access the EPG:**
    The EPG XML will be available at: `http://127.0.0.1:5001/epg.xml`

3.  **Stop and Remove Containers:**
    To stop and remove the container, network, and volumes defined in `docker-compose.yml`:
    ```bash
    docker compose down
    ```