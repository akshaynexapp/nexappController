import $ from"jquery";function django$($sel){if(typeof window.grp==="undefined"){return $($sel);}
if(window.grp.jQuery.fn.init===$.fn.init){return $($sel);}
const $djangoSel=$($sel);if($sel.prevObject){$djangoSel.prevObject=django$($sel.prevObject);}
return $djangoSel;}
export default django$;