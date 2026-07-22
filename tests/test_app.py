def test_hospital_registration_page_loads(client):
    """Test that the hospital registration page loads successfully."""
    response = client.get("/hospital_registration")
    assert response.status_code == 200
    assert b"Hospital Registration" in response.data
    assert b"MediChain" in response.data


def test_hospital_registration_submit_success(client):
    """Test submitting the hospital registration form successfully."""
    response = client.post(
        "/hospital_registration",
        data={
            "hospital_name": "ABC Hospital",
            "reg_number": "REG001",
            "hospital_type": "Government Hospital",
            "state": "Sindh",
            "city": "Karachi",
            "address": "Shahrah-e-Faisal",
            "postcode": "75400",
            "phone": "03001234567",
            "hospital_email": "hospital@test.com",

            "admin_name": "Ali Ahmed",
            "admin_ic": "42101-1234567-1",
            "admin_email": "admin@test.com",
            "admin_phone": "03121234567",
            "designation": "Director",
            "department": "Administration",

            "password": "Password@123",
            "confirm_password": "Password@123"
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    # Check success flash message appears in the response
    assert b"success" in response.data.lower() or b"registered" in response.data.lower()


def test_hospital_registration_duplicate_email(client):
    """Test that duplicate email returns a warning flash."""
    # First submission
    client.post(
        "/hospital_registration",
        data={
            "hospital_name": "ABC Hospital",
            "reg_number": "REG002",
            "hospital_type": "Government Hospital",
            "state": "Sindh",
            "city": "Karachi",
            "address": "Shahrah-e-Faisal",
            "postcode": "75400",
            "phone": "03001234567",
            "hospital_email": "dupe@test.com",
            "admin_name": "Ali Ahmed",
            "admin_ic": "42101-1234567-1",
            "admin_email": "admin@test.com",
            "admin_phone": "03121234567",
            "designation": "Director",
            "department": "Administration",
            "password": "Password@123",
            "confirm_password": "Password@123"
        },
        follow_redirects=True
    )

    # Second submission with same email
    response = client.post(
        "/hospital_registration",
        data={
            "hospital_name": "ABC Hospital",
            "reg_number": "REG003",
            "hospital_type": "Government Hospital",
            "state": "Sindh",
            "city": "Karachi",
            "address": "Shahrah-e-Faisal",
            "postcode": "75400",
            "phone": "03001234567",
            "hospital_email": "dupe@test.com",
            "admin_name": "Ali Ahmed",
            "admin_ic": "42101-1234567-1",
            "admin_email": "admin@test.com",
            "admin_phone": "03121234567",
            "designation": "Director",
            "department": "Administration",
            "password": "Password@123",
            "confirm_password": "Password@123"
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    # Should show danger flash message about duplicate
    assert b"danger" in response.data.lower() or b"already registered" in response.data.lower()


def test_hospital_registration_duplicate_reg_number(client):
    """Test that duplicate registration number returns a warning flash."""
    # First submission
    client.post(
        "/hospital_registration",
        data={
            "hospital_name": "ABC Hospital",
            "reg_number": "REG-DUPE",
            "hospital_type": "Government Hospital",
            "state": "Sindh",
            "city": "Karachi",
            "address": "Shahrah-e-Faisal",
            "postcode": "75400",
            "phone": "03001234567",
            "hospital_email": "unique@test.com",
            "admin_name": "Ali Ahmed",
            "admin_ic": "42101-1234567-1",
            "admin_email": "admin@test.com",
            "admin_phone": "03121234567",
            "designation": "Director",
            "department": "Administration",
            "password": "Password@123",
            "confirm_password": "Password@123"
        },
        follow_redirects=True
    )

    # Second submission with same reg number
    response = client.post(
        "/hospital_registration",
        data={
            "hospital_name": "ABC Hospital",
            "reg_number": "REG-DUPE",
            "hospital_type": "Government Hospital",
            "state": "Sindh",
            "city": "Karachi",
            "address": "Shahrah-e-Faisal",
            "postcode": "75400",
            "phone": "03001234567",
            "hospital_email": "another@test.com",
            "admin_name": "Ali Ahmed",
            "admin_ic": "42101-1234567-1",
            "admin_email": "admin@test.com",
            "admin_phone": "03121234567",
            "designation": "Director",
            "department": "Administration",
            "password": "Password@123",
            "confirm_password": "Password@123"
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    # Should show danger flash message about duplicate reg number
    assert b"danger" in response.data.lower() or b"already exists" in response.data.lower()
