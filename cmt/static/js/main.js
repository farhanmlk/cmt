document.addEventListener("DOMContentLoaded", function () {
  var btn = document.getElementById("hamburger");
  var nav = document.getElementById("navLinks");
  if (btn && nav) {
    btn.addEventListener("click", function () {
      nav.classList.toggle("open");
    });
  }
});
