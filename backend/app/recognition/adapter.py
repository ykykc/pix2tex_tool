from app.schemas.recognition import UploadedImageRequest


MOCK_LATEX = r"\frac{d\omega}{dt}=\frac{P_m-P_e}{2H}"


class MockRecognitionAdapter:
    def recognize(self, image: UploadedImageRequest) -> str:
        return MOCK_LATEX

