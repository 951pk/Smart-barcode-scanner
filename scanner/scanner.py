import cv2

try:
    from pyzbar.pyzbar import decode
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    print("Warning: pyzbar not installed. Install with: pip install pyzbar")


class CameraScanner:
    def __init__(self, camera_index=0):
        # Try DirectShow backend first (better on Windows)
        self.capture = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        
        if not self.capture.isOpened():
            # Fallback to default backend
            self.capture = cv2.VideoCapture(camera_index)

        # Set resolution
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # ✅ FIX: Use hasattr to safely enable autofocus (works with OpenCV 4 and 5)
        if hasattr(cv2, 'CAP_PROP_AUTOFOCUS'):
            try:
                self.capture.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            except Exception as e:
                print(f"Autofocus not supported: {e}")

        # Try to detect QR/Barcode using OpenCV's built-in detector as fallback
        try:
            self.qr_detector = cv2.QRCodeDetector()
        except Exception:
            self.qr_detector = None

    def is_open(self):
        return self.capture is not None and self.capture.isOpened()

    def read_frame(self):
        """Read a frame from camera and try to detect barcodes."""
        if not self.is_open():
            return None, []

        ret, frame = self.capture.read()
        if not ret or frame is None:
            return None, []

        decoded_values = []

        # Try pyzbar first (best for barcodes)
        if PYZBAR_AVAILABLE:
            try:
                barcodes = decode(frame)
                for barcode in barcodes:
                    data = barcode.data.decode('utf-8')
                    decoded_values.append(data)

                    # Draw rectangle around barcode
                    (x, y, w, h) = barcode.rect
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
                    cv2.putText(frame, data, (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            except Exception as e:
                print(f"pyzbar error: {e}")

        # Fallback to OpenCV QR detector
        if not decoded_values and self.qr_detector is not None:
            try:
                data, points, _ = self.qr_detector.detectAndDecode(frame)
                if data:
                    decoded_values.append(data)
                    if points is not None:
                        points = points.astype(int)
                        cv2.polylines(frame, [points[0]], True, (0, 255, 0), 3)
            except Exception as e:
                print(f"QR detector error: {e}")

        return frame, decoded_values

    def release(self):
        """Release the camera resource."""
        if self.capture is not None:
            self.capture.release()
            self.capture = None