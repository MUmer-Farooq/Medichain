def test_hospital_registration(client):

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