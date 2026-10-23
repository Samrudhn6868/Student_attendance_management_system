"""Load testing script using Locust framework."""

from locust import HttpUser, task, between, events
import random
import json
from datetime import date, timedelta


class StudentUser(HttpUser):
    """Simulate student user behavior."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Login when user starts."""
        # Use test credentials
        response = self.client.post('/login', data={
            'srn': 'PES1UG21CS001',
            'password': 'TestPassword123!'
        }, catch_response=True)
        
        if response.status_code != 200:
            response.failure(f"Login failed with status {response.status_code}")
    
    @task(3)
    def view_dashboard(self):
        """View student dashboard (most common action)."""
        with self.client.get('/student_dashboard', catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Dashboard failed with status {response.status_code}")
    
    @task(5)
    def view_attendance(self):
        """View attendance records (very common action)."""
        with self.client.get('/view_attendance', catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"View attendance failed with status {response.status_code}")
    
    @task(1)
    def view_attendance_page_2(self):
        """View second page of attendance (less common)."""
        with self.client.get('/view_attendance?page=2', catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"View attendance page 2 failed")
    
    def on_stop(self):
        """Logout when user stops."""
        self.client.get('/logout')


class TeacherUser(HttpUser):
    """Simulate teacher user behavior."""
    
    wait_time = between(2, 5)  # Teachers wait longer between actions
    
    def on_start(self):
        """Login when user starts."""
        response = self.client.post('/login', data={
            'srn': 'TCH001',
            'password': 'TeacherPassword123!'
        }, catch_response=True)
        
        if response.status_code != 200:
            response.failure(f"Teacher login failed with status {response.status_code}")
    
    @task(2)
    def view_faculty_dashboard(self):
        """View faculty dashboard."""
        with self.client.get('/faculty_dashboard', catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Faculty dashboard failed")
    
    @task(5)
    def mark_attendance(self):
        """Mark attendance for a student."""
        # Generate random student SRN and subject
        srn = f'PES1UG21CS{random.randint(1, 100):03d}'
        subjects = ['Mathematics', 'Physics', 'Chemistry', 'Computer Science', 'English']
        subject = random.choice(subjects)
        status = random.choice(['present', 'absent'])
        
        with self.client.post('/mark_attendance', data={
            'srn': srn,
            'subject': subject,
            'date': date.today().strftime('%Y-%m-%d'),
            'status': status
        }, catch_response=True) as response:
            if response.status_code not in [200, 302]:
                response.failure(f"Mark attendance failed with status {response.status_code}")
    
    @task(1)
    def view_attendance_reports(self):
        """View attendance reports (if endpoint exists)."""
        with self.client.get('/view_attendance', catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"View reports failed")
    
    def on_stop(self):
        """Logout when user stops."""
        self.client.get('/logout')


class MixedUserBehavior(HttpUser):
    """Simulate mixed user behavior (80% students, 20% teachers)."""
    
    wait_time = between(1, 4)
    
    def on_start(self):
        """Randomly login as student or teacher."""
        self.is_teacher = random.random() < 0.2  # 20% chance
        
        if self.is_teacher:
            response = self.client.post('/login', data={
                'srn': 'TCH001',
                'password': 'TeacherPassword123!'
            })
        else:
            response = self.client.post('/login', data={
                'srn': f'PES1UG21CS{random.randint(1, 100):03d}',
                'password': 'TestPassword123!'
            })
    
    @task
    def perform_action(self):
        """Perform action based on user type."""
        if self.is_teacher:
            # Teacher actions
            action = random.choice(['dashboard', 'mark_attendance'])
            if action == 'dashboard':
                self.client.get('/faculty_dashboard')
            else:
                self.client.post('/mark_attendance', data={
                    'srn': f'PES1UG21CS{random.randint(1, 100):03d}',
                    'subject': random.choice(['Math', 'Physics', 'Chemistry']),
                    'date': date.today().strftime('%Y-%m-%d'),
                    'status': random.choice(['present', 'absent'])
                })
        else:
            # Student actions
            action = random.choice(['dashboard', 'view_attendance', 'view_attendance'])
            if action == 'dashboard':
                self.client.get('/student_dashboard')
            else:
                self.client.get('/view_attendance')
    
    def on_stop(self):
        """Logout."""
        self.client.get('/logout')


class APIUser(HttpUser):
    """Simulate API endpoint usage."""
    
    wait_time = between(0.5, 2)
    
    def on_start(self):
        """Get API token or login."""
        # Adjust based on your API authentication
        pass
    
    @task
    def api_attendance_query(self):
        """Query attendance via API (if API endpoints exist)."""
        # Example: self.client.get('/api/attendance/PES1UG21CS001')
        pass
    
    @task
    def api_health_check(self):
        """Check API health endpoint (if exists)."""
        # Example: self.client.get('/api/health')
        pass


# Event listeners for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log slow requests."""
    if response_time > 1000:  # Slower than 1 second
        print(f"SLOW: {request_type} {name} took {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("Load test starting...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("Load test completed!")
    
    # Print statistics
    stats = environment.stats
    print(f"\nTotal requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99th percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")


# To run this load test:
# 1. Install locust: pip install locust
# 2. Run: locust -f perf/load_test.py --host=http://localhost:5000
# 3. Open browser to http://localhost:8089
# 4. Configure number of users and spawn rate
# 5. Start test and monitor results

# Command-line usage examples:
# - Headless mode: locust -f perf/load_test.py --headless --users 100 --spawn-rate 10 --run-time 60s --host=http://localhost:5000
# - With specific user class: locust -f perf/load_test.py --headless --users 50 --spawn-rate 5 StudentUser --host=http://localhost:5000
# - Generate report: Add --html=reports/load_test_report.html --csv=reports/load_test
