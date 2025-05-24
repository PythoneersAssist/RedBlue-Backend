> **Backend implementation for the Red-Blue game, designed for the Assist DUAL program.**

---

## 📚 Table of Contents

- [Getting Started](#getting-started)
- [Prerequisites](#prerequisites)
- [Quick Installation](#quick-installation)
- [Running the Server](#running-the-server)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)

---

## 🚀 Getting Started

1. **Install Python 3.12.5 or newer**
2. **Create a virtual environment**
    ```bash
    python -m venv .venv
    ```
3. **Activate the virtual environment**
    - On Windows:
      ```bash
      .\.venv\Scripts\activate
      ```
    - On macOS/Linux:
      ```bash
      source .venv/bin/activate
      ```
4. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```
5. **Install PostgreSQL 12 or newer**
6. **Create a `.env` file in the main directory:**
    ```env
    DB_USERNAME=example
    DB_PASSWORD=example
    DB_HOST=example
    DB_PORT=1234
    DB_NAME=example
    ```
7. **Run the main file**
    ```bash
    python main.py
    ```

---

## 🛠 Prerequisites

- Python 3.12.5+
- PostgreSQL 12+
- Required modules listed in `requirements.txt`

---

## ⚡ Quick Installation

```bash
git clone https://github.com/yourusername/RedBlue-Backend.git
cd RedBlue-Backend
pip install -r requirements.txt
```

---

## 🏃 Running the Server

```bash
python main.py
```

The server will start at [http://localhost:8080](http://localhost:8080) by default.

---

## 📖 API Endpoints

| Method | Endpoint         | Description           |
|--------|-----------------|------------------------|
| POST   | `/api/create`   | Create a game          |
| WS     | `/api/ws`       | Join a game            |
| WS     | `/api/chat`     | Join a chat session    |
| GET    | `/api/game`     | Get current game state |
| POST   | `/api/games`    | Fetch all games        |

---

## ⚙️ Configuration

Create a `.env` file in the root directory with the following content:

```env
DB_USERNAME=example
DB_PASSWORD=example
DB_HOST=example
DB_PORT=1234
DB_NAME=example
```

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---
