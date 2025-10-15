(function($){if(typeof $==="undefined") return;
$(function(){
  var $cat=$("#id_category");
  if(!$cat.length) return;
  $cat.on("change", function(){
    var cid=$(this).val(); if(!cid) return;
    var url=new URL(window.location.href);
    url.searchParams.set("category", cid);
    window.location.href=url.toString();
  });
});
})(window.django && django.jQuery ? django.jQuery : window.jQuery);