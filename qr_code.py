import qrcode

data = "http://127.0.0.1:8000/user/user-info/1/"

img = qrcode.make(data)
img.save("call_qr.png")