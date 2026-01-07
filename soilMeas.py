import Adafruit_ADS1x15
import time
import csv
import logging
from datetime import datetime
import os

# ===================== Configuration =====================
# ADC module gain setting (fixed at 1 for 0-5V input)
GAIN = 1
# Sampling interval (seconds) - 30 minutes = 1800 seconds
SAMPLING_INTERVAL = 1800
# Data save path
CSV_FILE_PATH = "soil_moisture_data.csv"
# Log save path
LOG_FILE_PATH = "sensor_logs.log"

# ===================== Initialization =====================
# Configure logging (record runtime status and error messages)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, encoding="utf-8"),
        logging.StreamHandler()  # Output to console simultaneously
    ]
)

# Initialize ADS1115 ADC module
try:
    adc = Adafruit_ADS1x15.ADS1115()
    logging.info("ADS1115 ADC module initialized successfully")
except Exception as e:
    logging.error(f"ADC module initialization failed: {str(e)}")
    raise SystemExit(1)

# Initialize CSV file (create header if not exists)
if not os.path.exists(CSV_FILE_PATH):
    with open(CSV_FILE_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "adc_value", "voltage", "moisture_percent"])
    logging.info(f"CSV file created: {CSV_FILE_PATH}")

# ===================== Core Functions =====================
def read_soil_moisture():
    """
    Read soil moisture data:
    1. Read raw ADC value → Convert to voltage → Convert to moisture percentage
    2. Moisture % = 100 - (voltage/5.0 × 100) (higher moisture = lower voltage)
    """
    try:
        # Read data from ADS1115 Channel A0 (FC-28 A0 pin connected here)
        adc_value = adc.read_adc(0, gain=GAIN)
        
        # Convert to voltage (ADS1115 range: 0-65535 → corresponds to 0-5V)
        voltage = (adc_value / 65535.0) * 5.0
        
        # Convert to moisture percentage (2 decimal places)
        moisture_percent = round(100 - (voltage / 5.0 * 100), 2)
        
        # Boundary correction (avoid abnormal values)
        moisture_percent = max(0.0, min(100.0, moisture_percent))
        
        logging.debug(f"Raw ADC value: {adc_value} | Voltage: {voltage:.2f}V | Moisture: {moisture_percent}%")
        return adc_value, voltage, moisture_percent
    
    except Exception as e:
        logging.error(f"Failed to read moisture data: {str(e)}")
        return None, None, None

def save_to_csv(timestamp, adc_value, voltage, moisture_percent):
    """Save data to CSV file"""
    try:
        with open(CSV_FILE_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                adc_value,
                round(voltage, 2),
                moisture_percent
            ])
        logging.info(f"Data saved: {timestamp} | Moisture: {moisture_percent}%")
    except Exception as e:
        logging.error(f"Failed to save to CSV: {str(e)}")

# ===================== Main Program =====================
if __name__ == "__main__":
    logging.info("Soil moisture collection program started (press Ctrl+C to stop)")
    try:
        while True:
            # Get current timestamp
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Read moisture data
            adc_val, volt, moist = read_soil_moisture()
            
            # Save data if valid
            if all(v is not None for v in [adc_val, volt, moist]):
                save_to_csv(current_time, adc_val, volt, moist)
            
            # Wait for next sampling
            logging.info(f"Waiting {SAMPLING_INTERVAL/60} minutes for next collection...")
            time.sleep(SAMPLING_INTERVAL)
    
    except KeyboardInterrupt:
        logging.info("Program stopped manually by user")
    except Exception as e:
        logging.critical(f"Program terminated abnormally: {str(e)}")
    finally:
        logging.info("Program exited")
