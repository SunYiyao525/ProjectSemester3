# Import necessary modules
import time
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import smbus  # For Raspberry Pi I2C communication to read soil moisture

# ====================== 1. Hardware Configuration (Raspberry Pi Read Soil Moisture) ======================
# Initialize I2C bus (Raspberry Pi default I2C bus is 1)
bus = smbus.SMBus(1)
# PCF8591 I2C address (default is 0x48)
PCF8591_ADDR = 0x48

# Function to read soil moisture
def read_soil_moisture():
    try:
        # Read analog input channel 0 of PCF8591 (connected to sensor AO pin)
        bus.write_byte(PCF8591_ADDR, 0x00)  # Select channel 0
        time.sleep(0.1)
        raw_value = bus.read_byte(PCF8591_ADDR)
        # Convert to moisture percentage (sensor output 0-255, 0=wettest, 255=driest, reverse conversion)
        moisture_percent = 100 - (raw_value / 255 * 100)
        return round(moisture_percent, 2)
    except Exception as e:
        print(f"Failed to read soil moisture: {e}")
        return "Reading failed"

# ====================== 2. Email Sending Configuration ======================
# Replace with your email information!!!
SMTP_SERVER = "smtp.qq.com"  # QQ email SMTP server (use smtp.163.com for 163 email)
SMTP_PORT = 587  # General port number
SENDER_EMAIL = "your_sender_email@qq.com"  # e.g., 123456@qq.com
SENDER_AUTH_CODE = "your_email_auth_code"  # Not login password! Get from email SMTP settings
RECEIVER_EMAIL = "receiver_email@xxx.com"  # e.g., 789012@163.com

# Function to send email
def send_email(moisture):
    # Email subject and content
    subject = f"Soil Moisture Monitoring Email {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
    content = f"""
    <p>Soil Moisture Monitoring Data Notification</p>
    <p>Current Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}</p>
    <p>Real-time Soil Moisture: {moisture}%</p>
    <p>This email is automatically sent every 3 hours</p>
    """
    
    # Construct email message
    msg = MIMEText(content, "html", "utf-8")
    msg["From"] = Header("Raspberry Pi Moisture Monitoring System", "utf-8")
    msg["To"] = Header("Monitoring Recipient", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    
    try:
        # Connect to email server and send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Enable TLS encryption
        server.login(SENDER_EMAIL, SENDER_AUTH_CODE)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

# ====================== 3. Core Time Judgment Logic (Based on Teacher's Code) ======================
if __name__ == "__main__":
    # Initialize start time (startTime from teacher's code)
    startTime = time.localtime().tm_hour + 8  # Time zone adaptation (+8 for Beijing Time)
    lastValue = startTime
    print(f"Program started, initial time: {startTime} o'clock, first email will be sent after 3 hours interval")
    
    # Infinite loop to monitor time and send emails
    while True:
        # Get current time in seconds since epoch
        seconds = time.time()
        # Convert to local time structure
        current_time = time.localtime(seconds)
        # Calculate current hour (+8 for Beijing Time)
        Current_Value = current_time.tm_hour + 8
        
        # Print real-time status (for debugging)
        print(f"\rCurrent time: {Current_Value} o'clock | Last send time: {lastValue} o'clock", end="")
        
        # Core judgment logic (from teacher's code)
        if lastValue == Current_Value:
            # Same hour, ignore
            pass
        else:
            # Calculate time difference
            difference = Current_Value - lastValue
            # Handle cross-day situation (e.g., lastValue=23, Current_Value=1 → difference=-22, actual 2 hours)
            if difference < 0:
                difference += 24  # Add 24 hours for cross-day calculation
            
            # Send email if time difference > 3 hours
            if difference > 3:
                print(f"\nTime difference {difference} hours (>3 hours), preparing to send email...")
                # Read current moisture value
                moisture = read_soil_moisture()
                # Send email with moisture data
                send_email(moisture)
                # Update last send time
                lastValue = Current_Value
            else:
                # Do not send email if time difference < 4 hours
                print(f"\nTime difference {difference} hours (<4 hours), no email sent")
                lastValue = Current_Value  # Update lastValue to avoid repeated judgment
        
        # Check time every 1 minute (avoid high resource usage from fast loop)
        time.sleep(60)
