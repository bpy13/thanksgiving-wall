import random
from PIL import Image
from io import BytesIO
from locust import HttpUser, task, events, between

def create_test_image():
    """Create a test image with random size and color using PIL"""
    height = random.randint(800, 4000)
    width = int(height * random.uniform(0.5, 1.5))
    # Random colors for variety
    colors = ['orange', 'red', 'blue', 'green', 'purple', 'yellow', 'brown']
    color = random.choice(colors)
    # Create the test image
    img = Image.new('RGB', (width, height), color=color)
    # Save to bytes
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes.getvalue()

# Sample test data for realistic content
SAMPLE_MESSAGES = [
    "感恩上帝的恩典和愛",
    "Thanks for all the blessings this year",
    "感謝家人朋友的陪伴",
    "Grateful for good health and happiness",
    "感恩教會大家庭的溫暖",
    "Thankful for this wonderful community",
    "感謝主耶穌的救恩",
    "Blessed to be part of this church family"
]

SAMPLE_NAMES = ["小明", "Mary", "John", "小華", "Sarah", "David", "小美", "Grace"]
SAMPLE_GROUPS = ["青年組", "Adult Group", "Family", "小組A", "Group B", "婦女團契"]

class UploaderUser(HttpUser):
    """Simulates users actively uploading messages and images"""
    wait_time = between(5, 15)  # Wait 5-15 seconds between requests
    def on_start(self):
        """Always visit root page when user starts"""
        self.client.get("/")
    
    @task(4)
    def upload_text_message(self):
        """Submit a text-only message (40% of the time)"""
        data = {
            'message': random.choice(SAMPLE_MESSAGES),
            'user_name': random.choice(SAMPLE_NAMES),
            'group_name': random.choice(SAMPLE_GROUPS),
            'event': 'Load Test'
        }
        with self.client.post(
            "/upload", data=data, catch_response=True) as response:
            result = response.json()
            if result.get('status') == 'success':
                response.success()
            else:
                response.failure()
    
    @task(1)
    def upload_message_with_image(self):
        """Submit a message with a test image"""
        data = {
            'message': random.choice(SAMPLE_MESSAGES),
            'user_name': random.choice(SAMPLE_NAMES),
            'group_name': random.choice(SAMPLE_GROUPS),
            'event': 'Load Test with Image'
        }
        # Generate a new random test image for each upload
        test_image_bytes = create_test_image()
        file = {'image': (
            'test_thanksgiving.jpg', BytesIO(test_image_bytes), 'image/jpeg'
        )}
        with self.client.post(
            "/upload", data=data, files=file, catch_response=True) as response:
            result = response.json()
            if result.get('status') == 'success':
                response.success()
            else:
                response.failure()

# Global variables to track test results
test_passed = True
failure_count = 0
total_requests = 0

@events.request.add_listener
def request_handler(exception=None, response=None, **kwargs):
    """Track request success/failure for CI/CD pipeline"""
    global test_passed, failure_count, total_requests
    total_requests += 1
    if exception or (response and response.status_code >= 400):
        failure_count += 1

@events.test_stop.add_listener
def test_stop_handler(**kwargs):
    """Final test evaluation for CI/CD pipeline"""
    global test_passed, failure_count, total_requests
    print(f'Total Requests: {total_requests}, Failures: {failure_count}')
    if failure_count > 0:
        exit(1)
    else:
        exit(0)
