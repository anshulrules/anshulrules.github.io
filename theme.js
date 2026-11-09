// 밤낮(다크모드) 전환. 처음에는 기기 설정을 따르고, 첫 페이지 로고를 누르면 바뀐다.
// 고른 값은 이 브라우저에만 저장되며, 기기 설정과 같아지면 다시 기기 설정을 따른다.
(function () {
  var root = document.documentElement;
  try { var t = localStorage.getItem("theme"); if (t) root.setAttribute("data-theme", t); } catch (e) {}
  document.addEventListener("click", function (e) {
    if (!e.target.closest || !e.target.closest(".night")) return;
    var sys = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    var next = (root.getAttribute("data-theme") || sys) === "dark" ? "light" : "dark";
    try {
      if (next === sys) { root.removeAttribute("data-theme"); localStorage.removeItem("theme"); }
      else { root.setAttribute("data-theme", next); localStorage.setItem("theme", next); }
    } catch (e) { root.setAttribute("data-theme", next); }
  });
})();
