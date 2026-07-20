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

// Submit Hospital Registration
function submitForm(event) {

  event.preventDefault();

  const agreeTerms = document.getElementById("agreeTerms");
  const agreeHipaa = document.getElementById("agreeHipaa");

  if (!agreeTerms.checked || !agreeHipaa.checked) {

    MediChain.showToast(
      "Please accept the terms and conditions.",
      "warning"
    );

    return;
  }

  const submitBtn = document.getElementById("submitBtn");

  submitBtn.innerHTML =
    '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';

  submitBtn.disabled = true;

  // Demo Submission
  setTimeout(() => {

    Swal.fire({

      icon: "success",

      title: "Application Submitted!",

      html:
        "Your hospital registration has been submitted.<br><small class='text-muted'>You will receive an email within 2–3 business days.</small>",

      confirmButtonText: "Back to Home",

      confirmButtonColor: "var(--primary)",

      customClass: {
        popup: "rounded-4"
      }

    }).then(() => {

      window.location.href = "/";

    });

  }, 1800);

}