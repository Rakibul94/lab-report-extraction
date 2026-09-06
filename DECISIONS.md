
I looked into three potential OCR engines for selecting RealOCR for the project: Tesseract, EasyOCR, RapidOCR.Since project requirements were OCR extraction should have success even if pictures have dim or poor lighting or parts being cropped out.EasyOCR and RapidOCR already does better here compared to Tesseract.Also another requirement was that OCR extraction should on both english and bengali language.Since EasyOCR already has it and no official module avaiable for RapidOCR for bengali text extraction.Hence,I finally picked EasyOCR as actual RealOCR for the project.


For testdata,I used real lab reports from hospitals like Popular, Square and BRB.I took one picture properly, another with poor lighting and the other cropped out.I also created a lab report with bangla on it for bilingual testing of the OCR engine.I took an empty paper and another normal paper with different content so that OCR can distinguish whether it is a lab report or not.

I also created json files as recordings for MOCKOCR testing.Two json files have actual contents of a lab report, another that has
both english and bangla content of a lab report.I also created blank json file and not other that has random contents so that MOCKOCR can distinguish what a lab report is or not in testing.