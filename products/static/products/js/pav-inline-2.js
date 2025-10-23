// products/js/pav-inline.js
(function ($) {
  if (typeof $ === "undefined") return;

  // ============ Helpers ============
  function findRow($el) {
    // پوشش تم‌های مختلف ادمین و inlineهای Tabular/Stacked
    return $el.closest("tr.form-row, .dynamic-productattributevalue_set, .inline-related");
  }

  function fields($row){
    return {
      attr:    $row.find("select[name$='-attribute']"),
      vtext:   $row.find("input[name$='-value_text']"),
      vint:    $row.find("input[name$='-value_int']"),
      vdec:    $row.find("input[name$='-value_decimal']"),
      vbool:   $row.find("select[name$='-value_bool'],input[name$='-value_bool']"),
      vchoice: $row.find("select[name$='-value_choice']"),
      vmulti:  $row.find("select[name$='-values_multi']")
    };
  }

  function showOnly($row, kind){
    var F = fields($row);
    // همیشه خود attribute فعال باشد
    F.attr.prop("disabled", false).closest("td, .form-row").show();

    // همهٔ فیلدهای مقدار را قفل/مخفی کن
    [F.vtext,F.vint,F.vdec,F.vbool,F.vchoice,F.vmulti].forEach(function ($el) {
      $el.prop("disabled", true).closest("td, .form-row").hide();
    });

    function on($el){ $el.prop("disabled", false).closest("td, .form-row").show(); }

    if (kind === "text")    on(F.vtext);
    else if (kind === "int")     on(F.vint);
    else if (kind === "decimal") on(F.vdec);
    else if (kind === "bool")    on(F.vbool);
    else if (kind === "choice")  on(F.vchoice);
    else if (kind === "multi")   on(F.vmulti);
  }

  // پرکردن select (تکی و چندتایی) + حفظ انتخاب‌های معتبر
  function fill($select, options){
    if (!$select.length) return;

    var isMulti = $select.prop("multiple");
    var cur = $select.val();
    if (!Array.isArray(cur)) cur = cur ? [String(cur)] : [];

    $select.empty().append($('<option/>',{value:"",text:"— انتخاب کنید —"}));

    (options || []).forEach(function (o) {
      $select.append($('<option/>',{value:String(o.id),text:o.label}));
    });

    // فقط مقادیرِ هنوز موجود را نگه داریم
    var exists = {};
    $select.find("option").each(function(){ exists[$(this).val()] = true; });
    var keep = cur.filter(function(v){ return exists[v]; });

    if (isMulti) {
      $select.val(keep);
    } else {
      $select.val(keep.length ? keep[0] : "");
    }
  }

  function resetChoiceFields($row){
    var F = fields($row);
    if (F.vchoice.length) F.vchoice.val("");
    if (F.vmulti.length)  F.vmulti.val([]);
  }

  // ====== فیکس قطعی آدرس endpoint ======
  function endpointUrl(){
    // اگر قبلاً به‌صراحت ست شده، همان را استفاده کن
    if (window.PAV && window.PAV.endpoint) return window.PAV.endpoint;
    if (typeof window.PAV_ENDPOINT !== "undefined" && window.PAV_ENDPOINT) return window.PAV_ENDPOINT;

    // از URL جاری بساز: /admin/products/product/<id>/change/  یا  /add/
    var p = window.location.pathname;

    // /product/123/change/  →  /product/
    p = p.replace(/\/\d+\/change\/?$/, "/");

    // /product/add/  →  /product/
    p = p.replace(/\/add\/?$/, "/");

    // اگر انتهای مسیر /product/123/ مانده باشد  →  /product/
    p = p.replace(/\/\d+\/$/, "/");

    return p + "attribute-choices/";
  }

  function loadChoices($row, attrId){
    if (!attrId){
      showOnly($row, null);
      return;
    }

    resetChoiceFields($row);

    $.get(endpointUrl(), { attr: attrId }).done(function (resp) {
      var kind = resp && resp.kind ? resp.kind : null;
      var data = (resp && resp.data) || [];

      var F = fields($row);
      fill(F.vchoice, data);
      fill(F.vmulti,  data);

      // اگر تکی بود، چندتایی را مخفی کن و برعکس
      if (kind === "choice"){
        F.vmulti.prop("disabled", true).closest("td, .form-row").hide();
      } else if (kind === "multi"){
        F.vchoice.prop("disabled", true).closest("td, .form-row").hide();
      }

      showOnly($row, kind);
    }).fail(function () {
      // اگر به هر دلیلی endpoint در دسترس نبود، همهٔ فیلدهای مقدار بسته بماند
      showOnly($row, null);
    });
  }

  function bindExistingRows(){
    $("select[name$='-attribute']").each(function(){
      var $attr = $(this);
      var $row  = findRow($attr);
      showOnly($row, null);     // ابتدا همه را ببند
      var initAid = $attr.val();
      if (initAid) loadChoices($row, initAid); // اگر از قبل attr داشت، گزینه‌ها را لود کن
    });
  }

  function boot(){
    // تغییر ویژگی در هر ردیف
    $(document).off("change.pav", "select[name$='-attribute']")
      .on("change.pav", "select[name$='-attribute']", function(){
        var $row = findRow($(this));
        loadChoices($row, $(this).val());
      });

    // ردیف تازه اضافه شد
    $(document).on("formset:added", function (e, $row){
      var $attr = $row.find("select[name$='-attribute']");
      showOnly($row, null);
      var initAid = $attr.val();
      if (initAid) loadChoices($row, initAid);
    });

    bindExistingRows();
  }

  $(document).ready(boot);
})(window.django && django.jQuery ? django.jQuery : window.jQuery);
