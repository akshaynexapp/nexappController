import $ from"jquery";function grp$($sel){if(typeof window.grp==="undefined"){return $($sel);}
if(window.grp.jQuery.fn.init===$.fn.init){return $($sel);}
const $grpSel=window.grp.jQuery($sel);if($sel.prevObject){$grpSel.prevObject=grp$($sel.prevObject);}
return $grpSel;}
export default grp$;