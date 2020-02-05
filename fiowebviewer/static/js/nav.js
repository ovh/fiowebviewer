function getNavHeight(){
    return document.getElementById('navbar').clientHeight;
}

function setNavBar(navbarHeight){
    $("body").css("margin-top", navbarHeight+5);
    $("a.anchor-link").css("top", 0-navbarHeight);
}
$(document).ready(function(){
    setNavBar(getNavHeight());
});
$(window).resize(function(){
    setNavBar(getNavHeight());
});
