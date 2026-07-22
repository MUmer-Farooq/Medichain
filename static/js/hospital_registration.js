// =========================================
// Hospital Registration Functions
// =========================================

// Track current step
let currentStep = 1;

// Change Step
function goStep(step) {

  const currentStepContent = document.getElementById(`step${currentStep}`);
  const currentIndicator = document.getElementById(`si-${currentStep}`);

  if (currentStepContent) {
    currentStepContent.classList.remove("active");
  }

  if (currentIndicator) {
    currentIndicator.classList.remove("active");

    if (step > currentStep) {
      currentIndicator.classList.add("done");
    }
  }

  currentStep = step;

  const nextStepContent = document.getElementById(`step${step}`);
  const nextIndicator = document.getElementById(`si-${step}`);

  if (nextStepContent) {
    nextStepContent.classList.add("active");
  }

  if (nextIndicator) {
    nextIndicator.classList.add("active");
  }

  window.scrollTo({
    top: 0,
    behavior: "smooth"
  });
}
// Validate Required Fields Before Moving to Next Step
function validateStep(nextStep) {

  const currentStepContent = document.getElementById(`step${currentStep}`);
  const requiredFields = currentStepContent.querySelectorAll("[required]");

  for (let field of requiredFields) {

    // Skip hidden file inputs
    if (field.type === "file") {
      if (field.files.length === 0) {
        Swal.fire({
          icon: "warning",
          title: "Required Fields Missing",
          text: "Please fill all required fields before continuing."
        });
        return;
      }
    }
    else if (field.type === "checkbox") {
      if (!field.checked) {
        Swal.fire({
          icon: "warning",
          title: "Required Fields Missing",
          text: "Please fill all required fields before continuing."
        });
        field.focus();
        return;
      }
    }
    else if (field.value.trim() === "") {
      Swal.fire({
        icon: "warning",
        title: "Required Fields Missing",
        text: "Please fill all required fields before continuing."
      });

      field.focus();
      return;
    }
  }

  goStep(nextStep);
}

// Display Uploaded File Name
function showFile(input, targetId) {

  if (input.files && input.files.length > 0) {

    const target = document.getElementById(targetId);

    if (target) {
      target.textContent = `✓ ${input.files[0].name}`;
    }
  }

}

//load review data from form to review step

function loadReview() {
  const f = (name) => {
    const el = document.querySelector(`[name="${name}"]`);
    return el ? el.value : '';
  };
  const selectText = (name) => {
    const el = document.querySelector(`[name="${name}"]`);
    return el ? el.options[el.selectedIndex].text : '';
  };

  document.getElementById('reviewHospitalName').textContent = f('hospital_name');
  document.getElementById('reviewRegNumber').textContent = f('reg_number');
  document.getElementById('reviewHospitalType').textContent = selectText('hospital_type');
  document.getElementById('reviewCity').textContent = f('city');
  document.getElementById('reviewState').textContent = selectText('state');
  document.getElementById('reviewAddress').textContent = f('address');
  document.getElementById('reviewPhone').textContent = f('phone');
  document.getElementById('reviewHospitalEmail').textContent = f('hospital_email');
  document.getElementById('reviewPostcode').textContent = f('postcode');
  document.getElementById('reviewWebsite').textContent = f('website') || "N/A";
  document.getElementById('reviewBedCapacity').textContent = f('bed_capacity') || "N/A";

  document.getElementById('reviewAdminName').textContent = f('admin_name');
  document.getElementById('reviewAdminEmail').textContent = f('admin_email');
  document.getElementById('reviewDesignation').textContent = f('designation');
  document.getElementById('reviewAdminPhone').textContent = f('admin_phone');
  document.getElementById('reviewAdminIc').textContent = f('admin_ic');
  document.getElementById('reviewDepartment').textContent = f('department') || "N/A";

  // Document names
  const doc1 = document.getElementById('doc1');
  const doc2 = document.getElementById('doc2');
  const doc3 = document.getElementById('doc3');
  const doc4 = document.getElementById('doc4');

  document.getElementById('reviewDoc1').textContent = doc1 && doc1.files.length > 0 ? doc1.files[0].name : "Not uploaded";
  document.getElementById('reviewDoc2').textContent = doc2 && doc2.files.length > 0 ? doc2.files[0].name : "Not uploaded";
  document.getElementById('reviewDoc3').textContent = doc3 && doc3.files.length > 0 ? doc3.files[0].name : "Not uploaded";
  document.getElementById('reviewDoc4').textContent = doc4 && doc4.files.length > 0 ? doc4.files[0].name : "Not uploaded";
}

function reviewAndGo() {
  // Validate required fields in step 3 first (documents)
  const step3 = document.getElementById('step3');
  const requiredFields = step3.querySelectorAll("[required]");
  for (let field of requiredFields) {
    if (field.type === "file" && field.files.length === 0) {
      Swal.fire({
        icon: "warning",
        title: "Required Fields Missing",
        text: "Please upload all required documents before reviewing."
      });
      return;
    }
  }
  loadReview();
  goStep(4);
}

// Submit Hospital Registration
function submitForm(event) {

  const agreeTerms = document.getElementById("agreeTerms");
  const agreeHipaa = document.getElementById("agreeHipaa");

  if (!agreeTerms.checked || !agreeHipaa.checked) {

    MediChain.showToast(
      "Please accept the terms and conditions.",
      "warning"
    );

    event.preventDefault();
    return;
  }

  const submitBtn = document.getElementById("submitBtn");

  submitBtn.innerHTML =
    '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';

  submitBtn.disabled = true;

  // Allow the form to submit naturally to Flask backend
  return true;

}
