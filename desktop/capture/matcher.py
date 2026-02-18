import cv2
import numpy as np
import os
import glob


class DigitMatcher:
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

    def __init__(self):
        self.templates = {}  # digit -> list of template images
        self.load_templates()

    def load_templates(self):
        """Load digit template images (0-9) from templates directory."""
        for digit in range(10):
            pattern = os.path.join(self.TEMPLATE_DIR, f"{digit}_*.png")
            files = glob.glob(pattern)
            if not files:
                pattern = os.path.join(self.TEMPLATE_DIR, f"{digit}.png")
                files = glob.glob(pattern)
            self.templates[digit] = [cv2.imread(f, cv2.IMREAD_GRAYSCALE) for f in files]

    def preprocess(self, image):
        """Convert to grayscale, apply threshold, remove noise."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        # Apply binary threshold
        _, binary = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        # Remove noise with morphological operations
        kernel = np.ones((2, 2), np.uint8)
        clean = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        return clean

    def find_digit_regions(self, binary_image):
        """Find individual digit bounding boxes using contour detection."""
        contours, _ = cv2.findContours(
            binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        boxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h > 5 and w > 2:  # Filter noise
                boxes.append((x, y, w, h))
        # Sort left to right
        boxes.sort(key=lambda b: b[0])
        return boxes

    def match_digit(self, digit_image):
        """Match a single digit image against all templates, return best match digit."""
        best_score = -1
        best_digit = -1
        for digit, templates in self.templates.items():
            for tmpl in templates:
                if tmpl is None:
                    continue
                # Resize digit image to match template size
                resized = cv2.resize(digit_image, (tmpl.shape[1], tmpl.shape[0]))
                result = cv2.matchTemplate(resized, tmpl, cv2.TM_CCOEFF_NORMED)
                score = result.max()
                if score > best_score:
                    best_score = score
                    best_digit = digit
        return best_digit, best_score

    def recognize_number(self, image, min_confidence=0.5):
        """Recognize a multi-digit number from an image.
        Returns (number, confidence) or (None, 0) if failed."""
        binary = self.preprocess(image)
        boxes = self.find_digit_regions(binary)

        if not boxes:
            return None, 0.0

        digits = []
        confidences = []
        for x, y, w, h in boxes:
            digit_img = binary[y : y + h, x : x + w]
            digit, conf = self.match_digit(digit_img)
            if conf >= min_confidence:
                digits.append(str(digit))
                confidences.append(conf)
            else:
                return None, 0.0

        if not digits:
            return None, 0.0

        number = int("".join(digits))
        avg_confidence = sum(confidences) / len(confidences)
        return number, avg_confidence

    def has_templates(self):
        """Check if any templates are loaded."""
        return any(len(tmpls) > 0 for tmpls in self.templates.values())

    @staticmethod
    def extract_templates_from_image(image, output_dir, label_prefix=""):
        """Helper to extract individual digit images from a reference screenshot.
        User manually labels them afterwards."""
        os.makedirs(output_dir, exist_ok=True)
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        _, binary = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        boxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h > 5 and w > 2:
                boxes.append((x, y, w, h))
        boxes.sort(key=lambda b: b[0])
        for i, (x, y, w, h) in enumerate(boxes):
            digit_img = gray[y : y + h, x : x + w]
            path = os.path.join(output_dir, f"{label_prefix}digit_{i}.png")
            cv2.imwrite(path, digit_img)
        return len(boxes)
