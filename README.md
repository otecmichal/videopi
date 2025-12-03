## 🚪 RPI Zero 2W Video Doorbell PoC

This project is a Proof-of-Concept (PoC) for a low-latency, multi-feed video display system running on the **Raspberry Pi Zero 2W**. It demonstrates core logic for decoding RTSP streams, maintaining aspect ratio, and cycling between multiple camera feeds.

***

### 🌟 Current Status: Flask Mock-up (Web Interface)

The current state of the code uses a **Flask web server** to simulate the stream output, allowing for easy testing and debugging via a web browser (Chrome, Safari, etc.).

| Feature | Status | Description |
| :--- | :--- | :--- |
| **Video Source** | ✅ Functional | Decodes live **RTSP streams** defined in the local `feeds.json` file. |
| **Multi-Feed Logic** | ✅ Functional | Tracks `CURRENT_FEED_INDEX` and cycles through all configured streams. |
| **Aspect Ratio** | ✅ Implemented | Uses **letterboxing** to correctly scale the $16:9$ video into the $320 \times 240$ (4:3) display frame. |
| **Input Simulation** | ✅ Hardened | Uses **"PREV"** and **"NEXT"** links on the web page to trigger stream switching, simulating future physical button/touch input. |
| **Stream Stability** | ✅ Hardened | Employs a **`STREAM_VERSION`** counter and a grace period (`time.sleep`) to force the graceful shutdown of the previous stream thread before starting the new one, which is vital for stability on the RPi Zero 2W. |
| **Visual Indicators** | ✅ Implemented | Static **left and right arrow icons** are overlaid on the stream, marking the intended touch zones for feed cycling. |

***

### 🛣️ Next Steps: Transition to Headless

The next phase involves moving from the resource-heavy Flask web server to the final **single-threaded, headless** application, which is significantly more efficient and suitable for the RPi Zero 2W.

| Task | Goal |
| :--- | :--- |
| **Remove Flask** | Eliminate the multi-threaded web server overhead and HTTP latency. |
| **Display Integration** | Implement code for writing raw NumPy data to the **SPI display framebuffer**. This bypasses costly JPEG encoding and compression. |
| **Input Integration** | Implement the **`RPi.GPIO`** handler to trigger the `cycle_feed()` function via physical buttons or touch inputs (interrupt-driven). |
| **Single Loop** | Refactor the stream logic into one continuous `main_loop()` that handles input, decoding, processing, and display sequentially. |

***

### 🔐 Security & Configuration

The project follows best practices for credential management:

* **Sensitive Data:** All camera credentials (IPs, usernames, passwords) are stored in the **local** `feeds.json` file.
* **Version Control:** The production `feeds.json` file is listed in **`.gitignore`** and will not be tracked or committed to the remote repository, protecting sensitive information.
* A **`feeds.json.template`** file should be maintained and committed to the repository to provide the necessary configuration structure.
