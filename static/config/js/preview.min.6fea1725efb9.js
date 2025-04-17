"use strict";django.jQuery(function($){var overlay=$('.djnjc-overlay'),html=$('html'),inner=overlay.find('.inner'),preview_url=$('.previewlink').attr('data-url');var openPreview=function(){var selectors='input[type=text], input[type=hidden], select, textarea',fields=$(selectors,'#content-main form').not('#id_config_jsoneditor *'),$id=$('#id_uuid'),data={},loadingOverlay=$('#loading-overlay');loadingOverlay.show();if($id.length){data.id=$id.val();}
fields.each(function(i,field){var $field=$(field),name=$field.attr('name');if(!name||name.indexOf('initial-')===0||name.indexOf('config-__')===0||name.indexOf('_FORMS')!=-1){return;}
if(name.indexOf('config-0-')===0){name=name.replace('config-0-','');}
if($field.attr('name')==='organization'&&$field.val()==='null'){$field.val('');}
data[name]=$field.val();});$.post(preview_url,data,function(htmlContent){inner.html($('#content-main div',htmlContent).html());overlay.show();html.css('overflow','hidden');overlay.find('pre').trigger('click');overlay.find('.close').click(function(e){e.preventDefault();closePreview();});loadingOverlay.fadeOut(250);}).fail(function(xhr){if(xhr.status==400){alert('There was an issue while generating the preview \n'+'Details: '+xhr.responseText);}
else{var message='Error while generating preview';if(gettext){message=gettext(message);}
alert(message+':\n\n'+xhr.responseText);}
closePreview();});};var closePreview=function(){overlay.hide();inner.html('');html.attr('style','');};$('.previewlink').click(function(e){var configUi=$('#id_config_jsoneditor, #id_config-0-config_jsoneditor'),message;e.preventDefault();if(configUi.length){openPreview();}
else{message='No configuration available';if(gettext){message=gettext(message);}
alert(message);}});$(document).keyup(function(e){if(e.altKey&&e.which==80){$(document.activeElement).trigger('blur');setTimeout(openPreview,15);}
else if(!e.ctrlKey&&e.which==27){closePreview();}});});