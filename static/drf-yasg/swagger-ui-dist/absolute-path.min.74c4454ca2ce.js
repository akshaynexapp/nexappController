const getAbsoluteFSPath=function(){if(typeof module!=="undefined"&&module.exports){return require("path").resolve(__dirname)}
throw new Error('getAbsoluteFSPath can only be called within a Nodejs environment');}
module.exports=getAbsoluteFSPath