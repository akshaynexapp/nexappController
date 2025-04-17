'use strict';(function($){var form='#content-main form',mapValues=function(object){$('input, select, textarea',form).each(function(i,el){var field=$(el),name=field.attr('name'),value=field.val(),jsonValues=['config','config-0-config','config-0-context','devicelocation-0-geometry'];if(!name||name.substr(0,1)=='_'||name.substr(0,8)=='initial-'||name=='csrfmiddlewaretoken'||name.indexOf('__prefix__')>=0||name.indexOf('root')===0){return;}
if(field.attr('type')=='checkbox'){object[name]=field.is(':checked');}
else{object[name]=value;}
if(jsonValues.indexOf(name)>-1){try{object[name]=JSON.parse(value);}
catch(ignore){}}});$(document).trigger('owcInitialValuesLoaded');};var unsavedChanges=function(e){var currentValues={};mapValues(currentValues);var changed=false,message='You haven\'t saved your changes yet!',initialValue,name;if(currentValues.organization===''){currentValues.organization='null';}
if(gettext){message=gettext(message);}
for(name in django._owcInitialValues){initialValue=django._owcInitialValues[name];if(!objectIsEqual(initialValue,currentValues[name])){changed=true;break;}}
if(changed){e.returnValue=message;return message;}};var objectIsEqual=function(obj1,obj2){if(typeof obj1!='object'&&typeof obj2!='object'){return obj1==obj2;}
var obj1Type=typeof obj1,obj2Type=typeof obj2;if(obj1Type!=obj2Type){return false;}
var p;for(p in obj1){switch(typeof obj1[p]){case'object':if(!objectIsEqual(obj1[p],obj2[p])){return false;}break;default:if(obj1[p]!=obj2[p]){return false;}}}
for(p in obj2){if(obj1[p]===undefined){return false;}}
return true;};$(function($){if(!$('.submit-row').length){return;}
django._owcInitialValues={};mapValues(django._owcInitialValues);$(form).submit(function(){$(window).unbind('beforeunload',unsavedChanges);});$(window).bind('beforeunload',unsavedChanges);});}(django.jQuery));