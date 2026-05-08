from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_doc_orientation_classify=False, 
    use_doc_unwarping=False, 
    use_textline_orientation=False)

result = ocr.predict("data/Stage1/D0001.jpg")
for res in result:
    res.print()
    res.save_to_img("outputs")
    res.save_to_json("outputs")