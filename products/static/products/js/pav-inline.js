(function ($) {
  if (typeof $ === "undefined") return;

  // === کمکی‌ها ===
  function findRow($el) {
    // پوشش تم‌های مختلف ادمین و inline‌های Tabular/Stacked
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
    F.attr.prop("disabled", false).closest("td, .form-row").show();

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

  function fill($select, options){
    if (!$select.length) return;
    var cur = $select.val();
    $select.empty().append($('<option/>',{value:"",text:"— انتخاب کنید —"}));
    (options || []).forEach(function (o) {
      $select.append($('<option/>',{value:o.id,text:o.label}));
    });
    if (cur) $select.val(cur);
  }

  function resetChoiceFields($row){
    var F = fields($row);
    if (F.vchoice.length) F.vchoice.val("");
    if (F.vmulti.length)  F.vmulti.val([]);
  }

  function endpointUrl(){
    if (window.PAV && window.PAV.endpoint) return window.PAV.endpoint;
    if (typeof window.PAV_ENDPOINT !== "undefined" && window.PAV_ENDPOINT) return window.PAV_ENDPOINT;
    var here = window.location.pathname.replace(/\/(add|change)\/?$/, "/");
    return here + "attribute-choices/";
  }

  function loadChoices($row, attrId){
    if (!attrId){ showOnly($row, null); return; }

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
      showOnly($row, null);
    });
  }

  function bindExistingRows(){
    $("select[name$='-attribute']").each(function(){
      var $attr = $(this);
      var $row  = findRow($attr);
      showOnly($row, null);
      var initAid = $attr.val();
      if (initAid) loadChoices($row, initAid);
    });
  }

  function boot(){
    // تغییر ویژگی در هر ردیف
    $(document).off("change.pav", "select[name$='-attribute']")
      .on("change.pav", "select[name$='-attribute']", function(){
        var $row = findRow($(this));
        loadChoices($row, $(this).val());
      });

    // ردیف تازه
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
