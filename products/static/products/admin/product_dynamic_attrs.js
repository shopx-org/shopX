// وقتی دسته عوض شد، صفحه با پارامتر ?category=... رفرش می‌شود
(function($){
  $(function(){
    var $cat = $('#id_category');
    if(!$cat.length) return;
    $cat.on('change', function(){
      var val = $(this).val() || '';
      var url = new URL(window.location.href);
      url.searchParams.set('category', val);
      window.location.href = url.toString();
    });
  });
})(django.jQuery);
