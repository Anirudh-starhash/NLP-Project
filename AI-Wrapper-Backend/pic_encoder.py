import base64

# Open image file in binary mode
file_path2="D:\\LEARNING\\NLP-Project\\AI-Wrapper-Backend\\test_images\\Nikesh_Pic1.jpg"
with open(file_path2, "rb") as img_file:
    b64_string = base64.b64encode(img_file.read()).decode('utf-8')

print(b64_string)  # This string goes into your JSON request
