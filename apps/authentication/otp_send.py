# otp_email_timebased.py
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
import hmac
import time
import os

class OTPMailer:
    def __init__(
        self,
        username=None,
        password=None,
        mail_server=None,
        mail_port=None,
        use_ssl=True,
        default_sender=None,
        secret_key=None,
        otp_valid_seconds=300  # 5 menit
    ):
        self.username = username or os.getenv("MAIL_USERNAME", "kipen.dev@gmail.com")
        self.password = password or os.getenv("MAIL_PASSWORD", "")
        self.mail_server = mail_server or os.getenv("MAIL_SERVER", "smtp.gmail.com")
        self.mail_port = mail_port or int(os.getenv("MAIL_PORT", 465))
        self.use_ssl = use_ssl
        self.default_sender = default_sender or self.username
        self.secret_key = secret_key or os.getenv("OTP_SECRET_KEY", "Rahasia123")  # bisa di-set sendiri
        self.otp_valid_seconds = otp_valid_seconds

    def _generate_otp(self, email):
        """
        Generate OTP berdasarkan email + waktu
        Hanya 6 digit angka, berganti tiap otp_valid_seconds
        """
        interval = int(time.time() // self.otp_valid_seconds)
        msg = f"{email}-{interval}".encode()
        key = self.secret_key.encode()

        h = hmac.new(key, msg, hashlib.sha256).hexdigest()
        # ambil 6 digit terakhir angka
        digits = ''.join(filter(str.isdigit, h))[-6:]
        # jika kurang dari 6 digit, pad dengan random angka
        return digits.zfill(6)

    def send_otp(self, to_email, subject="Kode OTP RFID-SMANTU"):
        otp = self._generate_otp(to_email)

        # buat email
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.default_sender
        message["To"] = to_email

        text = f"Kode OTP Anda adalah: {otp} (berlaku {self.otp_valid_seconds//60} menit)"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; text-align: center; background-color: #f8f9fa; padding: 20px;">
            <div style="max-width: 500px; margin: auto; background: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #333;">Verifikasi Email</h2>
                <p>Gunakan kode OTP berikut untuk verifikasi akun Anda:</p>
                <div style="display: inline-block; padding: 15px 25px; font-size: 32px; font-weight: bold; 
                            color: white; background-color: #007bff; border-radius: 8px; margin: 20px 0;">
                    {otp}
                </div>
                <p style="margin-top: 10px; color: #555;">Kode ini berlaku {self.otp_valid_seconds//60} menit.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 12px; color: #999;">Jika Anda tidak meminta kode ini, abaikan email ini.</p>
            </div>
        </body>
        </html>
        """

        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        message.attach(part1)
        message.attach(part2)

        # kirim email
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(self.mail_server, self.mail_port, context=context) as server:
            server.login(self.username, self.password)
            server.sendmail(self.default_sender, to_email, message.as_string())

        print(f"✅ OTP {otp} berhasil dikirim ke {to_email}")
        return otp

    def verify_otp(self, to_email, otp_input):
        """Verifikasi OTP yang dikirim ke email, berdasarkan waktu"""
        valid_otp = self._generate_otp(to_email)
        return otp_input == valid_otp


mailer = OTPMailer(
    username="kipen.dev@gmail.com",
    password="thsy sdwe tiwf ftro",  # gunakan app password Gmail
    secret_key="31082008Sayang0914Grace0831Selalu14012009"
)