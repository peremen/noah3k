function fold(div_id, a_id){
    if (document.getElementById){
        div_o = document.getElementById(div_id);
        a_o = document.getElementById(a_id);
        if (div_o.style.display == "none"){
            div_o.style.display = "inline";
            a_o.innerHTML = "(접기)";
        } else {
            div_o.style.display = "none";
            a_o.innerHTML = "(펴기)";
        }
    }
}

function fold_without_text(el_id){
  var el = document.getElementById(el_id);
  el.style.display = (el.style.display == "") ? "none" : "";
}

