(function(){
  if (typeof window.PAV === "undefined") window.PAV = {};
  // تلاش برای خواندن از data-attribute در DOM (اگر قالب سفارشی داری)
  var el = document.getElementById("content-main");
  if (el && el.dataset && el.dataset.pavEndpoint) window.PAV.endpoint = el.dataset.pavEndpoint;

  // اگر بالا کار نکند، از contextvar که جنگو در قالب استاندارد تزریق می‌کند استفاده کن
  try {
    if (!window.PAV.endpoint && window.PAV_ENDPOINT) window.PAV.endpoint = window.PAV_ENDPOINT;
  } catch(e){}
})();
