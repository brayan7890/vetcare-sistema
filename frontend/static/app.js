const API="";let token=localStorage.getItem("vet_token")||null;let currentUser=null;let chartIngresos=null,chartEspecies=null,chartServicios=null;let propietariosCache=[];let _cobrarHistorialId=null;
async function api(path,opts={}){const h={"Content-Type":"application/json",...opts.headers};if(token)h["Authorization"]="Bearer "+token;const r=await fetch(API+path,{...opts,headers:h});if(r.status===401){logout();throw new Error("Sesion expirada")}if(r.status===204)return null;const d=await r.json();if(!r.ok){let m="Error";if(d.detail){m=typeof d.detail==="string"?d.detail:Array.isArray(d.detail)?d.detail.map(x=>x.msg||x).join("; "):JSON.stringify(d.detail)}throw new Error(m)}return d}
function showToast(m,ok=true){const t=document.getElementById("toast");t.textContent=m;t.className=`fixed bottom-6 right-6 z-50 px-5 py-3 rounded-xl shadow-lg text-sm font-medium text-white fade-in ${ok?"bg-brand-600":"bg-red-500"}`;setTimeout(()=>t.classList.add("hidden"),3000)}
function openModal(t){document.getElementById("modal-"+t).classList.remove("hidden");if(t==="paciente")fillPropietarioSelect("p-propietario");if(t==="cita")fillPacienteSelect("c-paciente");if(t==="historial")fillPacienteSelect("h-paciente");if(t==="comprobante"){fillPropietarioSelect("cb-propietario");loadServiciosSelect();initDetalles();setTimeout(()=>{const sel=document.getElementById("cb-propietario");sel.addEventListener("change",function(){const pid=parseInt(this.value);if(pid){const p=propietariosCache.find(x=>x.id===pid);if(p){document.getElementById("cb-cliente").value=p.nombre||"";document.getElementById("cb-ruc").value=p.ruc_dni||"";document.getElementById("cb-cliente").readOnly=true;document.getElementById("cb-ruc").readOnly=true}}else{document.getElementById("cb-cliente").value="";document.getElementById("cb-ruc").value="";document.getElementById("cb-cliente").readOnly=false;document.getElementById("cb-ruc").readOnly=false}})},200)}}
function closeModal(t){document.getElementById("modal-"+t).classList.add("hidden");const frm=document.getElementById("form-"+t);if(frm)frm.reset();if(t==="comprobante"){document.getElementById("detalles-container").innerHTML="";updateTotals();_cobrarHistorialId=null;var ce=document.getElementById("cb-cliente");var cr=document.getElementById("cb-ruc");if(ce)ce.readOnly=false;if(cr)cr.readOnly=false}}
function toggleMobile(){document.getElementById("mobile-nav").classList.toggle("hidden")}
async function handleLogin(e){e.preventDefault();document.getElementById("login-error").classList.add("hidden");const b=new URLSearchParams();b.append("username",document.getElementById("l-user").value);b.append("password",document.getElementById("l-pass").value);try{const r=await fetch(API+"/auth/login",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:b});const d=await r.json();if(!r.ok){if(r.status===423){showAuthError(d.detail);document.getElementById("l-pass").value="";return}throw new Error(d.detail||"Error")}loginSuccess(d)}catch(err){showAuthError(err.message)}}
function showAuthError(m){const e=document.getElementById("login-error");e.textContent=m;e.classList.remove("hidden")}
function loginSuccess(d){token=d.access_token;currentUser=d.user;localStorage.setItem("vet_token",token);enterApp()}
function logout(){token=null;currentUser=null;localStorage.removeItem("vet_token");document.getElementById("app-screen").classList.add("hidden");document.getElementById("auth-screen").classList.remove("hidden")}
async function enterApp(){document.getElementById("auth-screen").classList.add("hidden");document.getElementById("app-screen").classList.remove("hidden");document.getElementById("user-name").textContent=currentUser?.nombre||"";const re=document.getElementById("user-role");const rol=currentUser?.rol||"";const lb={admin:"ADMIN",veterinario:"VETERINARIO",recepcionista:"RECEPCIONISTA"};const cl={admin:"bg-red-100 text-red-700",veterinario:"bg-blue-100 text-blue-700",recepcionista:"bg-emerald-100 text-emerald-700"};re.textContent=lb[rol]||rol.toUpperCase();re.className=`hidden sm:inline-block text-xs px-2 py-0.5 rounded-full font-medium ${cl[rol]||"bg-gray-100"}`;buildNav();applyRBAC();showSection("dashboard")}
function buildNav(){const rol=currentUser?.rol||"";const ad=rol==="admin";const vt=rol==="veterinario"||ad;const bl=rol==="recepcionista"||ad;const items=[{id:"dashboard",icon:"fa-gauge-high",label:"Dashboard"},{id:"usuarios",icon:"fa-users",label:"Usuarios",ao:true},{id:"propietarios",icon:"fa-user-group",label:"Propietarios"},{id:"mascotas",icon:"fa-paw",label:"Mascotas"},{id:"citas",icon:"fa-calendar-check",label:"Citas"},{id:"historial",icon:"fa-notes-medical",label:"Historial",vo:true},{id:"inventario",icon:"fa-boxes-stacked",label:"Inventario"},{id:"facturacion",icon:"fa-file-invoice-dollar",label:"Facturacion",bo:true}];let h="";let m="";items.forEach(i=>{if(i.ao&&!ad)return;if(i.vo&&!vt)return;if(i.bo&&!bl)return;const c="px-3 py-2 rounded-md text-sm font-medium hover:bg-brand-600 transition";h+=`<button onclick="showSection('${i.id}')" class="${c}"><i class="fa-solid ${i.icon} mr-1"></i>${i.label}</button>`;m+=`<button onclick="showSection('${i.id}');toggleMobile()" class="block w-full text-left px-3 py-2 rounded-md text-sm font-medium hover:bg-brand-600">${i.label}</button>`});document.getElementById("nav-links").innerHTML=h;document.getElementById("mobile-nav").innerHTML=m}
function applyRBAC(){const rol=currentUser?.rol||"";const ad=rol==="admin";const vt=rol==="veterinario"||ad;const bl=rol==="recepcionista"||ad;document.querySelectorAll(".admin-section").forEach(e=>e.style.display=ad?"":"none");document.querySelectorAll(".vet-section").forEach(e=>e.style.display=vt?"":"none");document.querySelectorAll(".billing-section").forEach(e=>e.style.display=bl?"":"none");document.querySelectorAll(".admin-only").forEach(e=>e.style.display=ad?"":"none")}
async function tryAutoLogin(){if(!token)return;try{const r=await fetch(API+"/auth/me",{headers:{"Authorization":"Bearer "+token}});if(!r.ok)throw new Error();currentUser=await r.json();enterApp()}catch{logout()}}
const allSections=["dashboard","usuarios","propietarios","mascotas","citas","historial","inventario","facturacion"];
function showSection(n){allSections.forEach(s=>document.getElementById("sec-"+s).classList.toggle("hidden",s!==n));applyRBAC();if(n==="dashboard")loadDashboard();else if(n==="usuarios")loadUsuarios();else if(n==="propietarios")loadPropietarios();else if(n==="mascotas")loadMascotas();else if(n==="citas")loadCitas();else if(n==="historial")loadHistorial();else if(n==="inventario")loadInventario();else if(n==="facturacion")loadComprobantes()}
async function fillPropietarioSelect(sid){const s=document.getElementById(sid);if(!s)return;try{const d=await api("/propietarios");propietariosCache=d;s.innerHTML='<option value="">Seleccionar...</option>'+d.map(p=>`<option value="${p.id}">#${p.id} - ${p.nombre}</option>`).join("")}catch{s.innerHTML='<option value="">Error</option>'}}
async function fillPacienteSelect(sid){const s=document.getElementById(sid);if(!s)return;try{const[m,p]=await Promise.all([api("/pacientes"),api("/propietarios")]);const pm={};p.forEach(x=>pm[x.id]=x.nombre);s.innerHTML='<option value="">Seleccionar paciente...</option>'+m.map(x=>`<option value="${x.id}">${x.nombre} (${pm[x.propietario_id]||"?"})</option>`).join("")}catch{s.innerHTML='<option value="">Error</option>'}}
async function loadDashboard(){
try{
const d=await api("/api/dashboard");
const k=d.kpi;
const tendencia=k.ingresos_tendencia;
const tColor=tendencia>=0?"text-brand-600":"text-red-500";
const tIcon=tendencia>=0?"fa-arrow-up":"fa-arrow-down";
document.getElementById("dash-kpi").innerHTML=`
<div class="bg-white rounded-xl shadow p-4 fade-in"><div class="flex items-center gap-3"><div class="w-11 h-11 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center"><i class="fa-solid fa-sol"></i></div><div class="flex-1"><p class="text-xs text-gray-500">Ingresos del Mes</p><p class="text-xl font-bold text-gray-800">S/ ${k.ingresos_mes.toFixed(2)}</p></div><span class="text-xs font-semibold ${tColor}"><i class="fa-solid ${tIcon} mr-0.5"></i>${Math.abs(tendencia)}%</span></div></div>
<div class="bg-white rounded-xl shadow p-4 fade-in"><div class="flex items-center gap-3"><div class="w-11 h-11 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center"><i class="fa-solid fa-calendar-check"></i></div><div class="flex-1"><p class="text-xs text-gray-500">Total Citas</p><p class="text-xl font-bold text-gray-800">${k.citas_total}</p></div><div class="flex gap-1"><span class="text-xs bg-amber-100 text-amber-700 px-1.5 rounded">${k.citas_pendientes} pend.</span><span class="text-xs bg-brand-100 text-brand-700 px-1.5 rounded">${k.citas_atendidas} atend.</span></div></div></div>
<div class="bg-white rounded-xl shadow p-4 fade-in"><div class="flex items-center gap-3"><div class="w-11 h-11 rounded-xl bg-purple-100 text-purple-600 flex items-center justify-center"><i class="fa-solid fa-paw"></i></div><div class="flex-1"><p class="text-xs text-gray-500">Pacientes Activos</p><p class="text-xl font-bold text-gray-800">${k.pacientes}</p></div><span class="text-xs text-gray-400">${k.propietarios} propietarios</span></div></div>
<div class="bg-white rounded-xl shadow p-4 fade-in"><div class="flex items-center gap-3"><div class="w-11 h-11 rounded-xl ${k.inventario_bajo_stock>0?"bg-red-100 text-red-600":"bg-amber-100 text-amber-600"} flex items-center justify-center"><i class="fa-solid fa-boxes-stacked"></i></div><div class="flex-1"><p class="text-xs text-gray-500">Inventario</p><p class="text-xl font-bold text-gray-800">${k.inventario_total}</p></div>${k.inventario_bajo_stock>0?`<span class="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full font-medium"><i class="fa-solid fa-triangle-exclamation mr-0.5"></i>${k.inventario_bajo_stock}</span>`:""}</div></div>`;

const labels=d.ingresos_mensuales.map(x=>x.mes);
const data=d.ingresos_mensuales.map(x=>x.total);
if(chartIngresos)chartIngresos.destroy();
chartIngresos=new Chart(document.getElementById("chart-ingresos"),{type:"bar",data:{labels,datasets:[{label:"Ingresos (S/)",data,backgroundColor:"rgba(34,197,94,0.7)",borderRadius:6,borderSkipped:false}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,ticks:{callback:v=>"S/ "+v},grid:{color:"rgba(0,0,0,0.05)"}},x:{grid:{display:false}}}}});

const espLabels=d.especies.map(x=>x.especie);
const espData=d.especies.map(x=>x.cantidad);
const espColors=["#22c55e","#3b82f6","#a855f7","#f59e0b","#ef4444","#06b6d4"];
if(chartEspecies)chartEspecies.destroy();
chartEspecies=new Chart(document.getElementById("chart-especies"),{type:"doughnut",data:{labels:espLabels,datasets:[{data:espData,backgroundColor:espColors.slice(0,espLabels.length),borderWidth:2,borderColor:"#fff"}]},options:{responsive:true,maintainAspectRatio:false,cutout:"60%",plugins:{legend:{position:"bottom",labels:{boxWidth:12,padding:10,font:{size:11}}}}}});

const srvLabels=d.top_servicios.map(x=>x.nombre.length>18?x.nombre.substring(0,18)+"...":x.nombre);
const srvData=d.top_servicios.map(x=>x.cantidad);
if(chartServicios)chartServicios.destroy();
chartServicios=new Chart(document.getElementById("chart-servicios"),{type:"bar",data:{labels:srvLabels,datasets:[{label:"Unidades vendidas",data:srvData,backgroundColor:["#3b82f6","#06b6d4","#a855f7","#f59e0b","#ef4444","#22c55e"],borderRadius:6,borderSkipped:false}]},options:{indexAxis:"y",responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,grid:{color:"rgba(0,0,0,0.05)"}},y:{grid:{display:false}}}}});

const cstm=d.proximas_citas;
document.getElementById("citas-hoy-badge").textContent=cstm.length+" proximas";
document.getElementById("dash-citas-hoy").innerHTML=cstm.length?cstm.map(c=>{
const f=new Date(c.fecha);
const fechaStr=f.toLocaleDateString("es-PE",{day:"2-digit",month:"short"})+" "+f.toLocaleTimeString("es-PE",{hour:"2-digit",minute:"2-digit"});
const sc={Pendiente:"bg-yellow-100 text-yellow-700",Atendido:"bg-brand-100 text-brand-700",Cancelado:"bg-red-100 text-red-700"};
return `<div class="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 border border-gray-100">
<div class="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-xs font-bold">${f.getDate()}</div>
<div class="flex-1 min-w-0"><p class="text-sm font-medium text-gray-800 truncate">${c.paciente_nombre}</p><p class="text-xs text-gray-500 truncate">${c.motivo}</p></div>
<div class="flex flex-col items-end gap-1"><span class="text-xs text-gray-400">${fechaStr}</span><span class="text-xs px-1.5 py-0.5 rounded-full font-medium ${sc[c.estado]||"bg-gray-100"}">${c.estado}</span></div></div>`
}).join(""):'<p class="text-gray-400 text-sm text-center py-4">No hay citas pendientes</p>';

const al=d.alertas_inventario;
document.getElementById("alertas-badge").textContent=al.length+" alertas";
document.getElementById("dash-alertas").innerHTML=al.length?al.map(a=>{
if(a.tipo==="bajo_stock"){
return `<div class="flex items-center gap-3 p-2 rounded-lg bg-red-50 border border-red-100">
<div class="w-8 h-8 rounded-lg bg-red-100 text-red-600 flex items-center justify-center"><i class="fa-solid fa-box text-xs"></i></div>
<div class="flex-1 min-w-0"><p class="text-sm font-medium text-gray-800 truncate">${a.nombre}</p><p class="text-xs text-red-500">Stock: ${a.stock} / Min: ${a.stock_minimo}</p></div>
<button onclick="showSection('inventario')" class="text-xs text-blue-600 hover:underline">Ver</button></div>`
}
return `<div class="flex items-center gap-3 p-2 rounded-lg bg-amber-50 border border-amber-100">
<div class="w-8 h-8 rounded-lg bg-amber-100 text-amber-600 flex items-center justify-center"><i class="fa-solid fa-clock text-xs"></i></div>
<div class="flex-1 min-w-0"><p class="text-sm font-medium text-gray-800 truncate">${a.nombre}</p><p class="text-xs text-amber-600">Caduca: ${a.fecha_caducidad}</p></div></div>`
}).join(""):'<p class="text-gray-400 text-sm text-center py-4">Sin alertas</p>';

}catch(e){console.error("Dashboard:",e)}}
async function loadUsuarios(){try{const d=await api("/users");const rl={admin:"bg-red-100 text-red-700",veterinario:"bg-blue-100 text-blue-700",recepcionista:"bg-emerald-100 text-emerald-700"};const lb={admin:"Admin",veterinario:"Veterinario",recepcionista:"Recepcionista"};document.getElementById("tabla-usuarios").innerHTML=d.map(u=>
`<tr class="hover:bg-gray-50"><td class="px-4 py-3 text-sm">${u.id}</td><td class="px-4 py-3 text-sm font-medium">${u.username}</td><td class="px-4 py-3 text-sm">${u.nombre}</td><td class="px-4 py-3"><span class="text-xs px-2 py-0.5 rounded-full font-medium ${rl[u.rol]||"bg-gray-100"}">${lb[u.rol]||u.rol}</span></td><td class="px-4 py-3 text-sm">Activo</td><td class="px-4 py-3 text-center"><button onclick="deleteUsuario(${u.id})" class="text-red-500 hover:text-red-700 text-sm"><i class="fa-solid fa-trash"></i></button></td></tr>
`).join("")}catch(e){showToast(e.message,false)}}
async function submitUsuario(e){e.preventDefault();try{await api("/users",{method:"POST",body:JSON.stringify({username:document.getElementById("u-username").value,password:document.getElementById("u-pass").value,nombre:document.getElementById("u-nombre").value,rol:document.getElementById("u-rol").value})});showToast("Usuario creado");closeModal("usuario");loadUsuarios()}catch(e){showToast(e.message,false)}}
async function deleteUsuario(id){if(!confirm("Eliminar este usuario?"))return;try{await api("/users/"+id,{method:"DELETE"});showToast("Usuario eliminado");loadUsuarios()}catch(e){showToast(e.message,false)}}
async function loadPropietarios(){try{const d=await api("/propietarios");document.getElementById("tabla-propietarios").innerHTML=d.map(p=>
`<tr class="hover:bg-gray-50"><td class="px-4 py-3 text-sm">${p.id}</td><td class="px-4 py-3 text-sm font-medium">${p.nombre}</td><td class="px-4 py-3 text-sm">${p.telefono}</td><td class="px-4 py-3 text-sm">${p.email||"-"}</td><td class="px-4 py-3 text-sm">${p.ruc_dni||"-"}</td><td class="px-4 py-3 text-center space-x-2"><button onclick="openEditPropietario(${p.id},'${(p.nombre||"").replace(/'/g,"\\'")}','${(p.telefono||"").replace(/'/g,"\\'")}','${(p.email||"").replace(/'/g,"\\'")}','${(p.direccion||"").replace(/'/g,"\\'")}','${(p.ruc_dni||"").replace(/'/g,"\\'")}')" class="text-blue-500 hover:text-blue-700 text-sm"><i class="fa-solid fa-pen"></i></button><button onclick="deletePropietario(${p.id})" class="text-red-500 hover:text-red-700 text-sm"><i class="fa-solid fa-trash"></i></button></td></tr>
`).join("")}catch(e){showToast(e.message,false)}}
function openEditPropietario(id,n,t,e,d,r){document.getElementById("pr-nombre").value=n;document.getElementById("pr-telefono").value=t;document.getElementById("pr-email").value=e;document.getElementById("pr-direccion").value=d;document.getElementById("pr-ruc").value=r;const frm=document.getElementById("form-propietario");frm.onsubmit=async function(ev){ev.preventDefault();try{await api("/propietarios/"+id,{method:"PUT",body:JSON.stringify({nombre:document.getElementById("pr-nombre").value,telefono:document.getElementById("pr-telefono").value,email:document.getElementById("pr-email").value||null,direccion:document.getElementById("pr-direccion").value||null,ruc_dni:document.getElementById("pr-ruc").value||null})});showToast("Propietario actualizado");closeModal("propietario");frm.onsubmit=submitPropietario;loadPropietarios()}catch(err){showToast(err.message,false)}};openModal("propietario")}
async function submitPropietario(e){e.preventDefault();try{await api("/propietarios",{method:"POST",body:JSON.stringify({nombre:document.getElementById("pr-nombre").value,telefono:document.getElementById("pr-telefono").value,email:document.getElementById("pr-email").value||null,direccion:document.getElementById("pr-direccion").value||null,ruc_dni:document.getElementById("pr-ruc").value||null})});showToast("Propietario registrado");closeModal("propietario");loadPropietarios()}catch(e){showToast(e.message,false)}}
async function deletePropietario(id){if(!confirm("Eliminar este propietario?"))return;try{await api("/propietarios/"+id,{method:"DELETE"});showToast("Propietario eliminado");loadPropietarios()}catch(e){showToast(e.message,false)}}
async function loadMascotas(){try{const[m,p]=await Promise.all([api("/pacientes"),api("/propietarios")]);const pm={};p.forEach(x=>pm[x.id]=x.nombre);document.getElementById("tabla-mascotas").innerHTML=m.map(x=>
`<tr class="hover:bg-gray-50"><td class="px-4 py-3 text-sm font-medium">${x.nombre}</td><td class="px-4 py-3 text-sm">${x.especie}</td><td class="px-4 py-3 text-sm">${x.raza||"-"}</td><td class="px-4 py-3 text-sm">${x.sexo||"-"}</td><td class="px-4 py-3 text-sm">${x.peso?x.peso+" kg":"-"}</td><td class="px-4 py-3 text-sm">${pm[x.propietario_id]||"?"}</td><td class="px-4 py-3 text-center space-x-2"><button onclick="openEditPaciente(${x.id})" class="text-blue-500 hover:text-blue-700 text-sm"><i class="fa-solid fa-pen"></i></button><button onclick="deletePaciente(${x.id})" class="text-red-500 hover:text-red-700 text-sm"><i class="fa-solid fa-trash"></i></button></td></tr>
`).join("")}catch(e){showToast(e.message,false)}}
async function submitPaciente(e){e.preventDefault();try{await api("/pacientes",{method:"POST",body:JSON.stringify({nombre:document.getElementById("p-nombre").value,especie:document.getElementById("p-especie").value,raza:document.getElementById("p-raza").value||null,fecha_nacimiento:document.getElementById("p-fecha-nac").value||null,sexo:document.getElementById("p-sexo").value||null,esterilizado:document.getElementById("p-esterilizado").value==="true",peso:parseFloat(document.getElementById("p-peso").value)||null,notas:document.getElementById("p-notas").value||null,propietario_id:parseInt(document.getElementById("p-propietario").value)})});showToast("Mascota registrada");closeModal("paciente");loadMascotas()}catch(e){showToast(e.message,false)}}
async function openEditPaciente(id){try{const x=await api("/pacientes/"+id);await fillPropietarioSelect("p-propietario");document.getElementById("p-nombre").value=x.nombre;document.getElementById("p-especie").value=x.especie;document.getElementById("p-raza").value=x.raza||"";document.getElementById("p-fecha-nac").value=x.fecha_nacimiento||"";document.getElementById("p-sexo").value=x.sexo||"";document.getElementById("p-esterilizado").value=x.esterilizado?"true":"false";document.getElementById("p-peso").value=x.peso||"";document.getElementById("p-propietario").value=x.propietario_id;document.getElementById("p-notas").value=x.notas||"";const frm=document.getElementById("form-paciente");frm.onsubmit=async function(ev){ev.preventDefault();try{await api("/pacientes/"+id,{method:"PUT",body:JSON.stringify({nombre:document.getElementById("p-nombre").value,especie:document.getElementById("p-especie").value,raza:document.getElementById("p-raza").value||null,fecha_nacimiento:document.getElementById("p-fecha-nac").value||null,sexo:document.getElementById("p-sexo").value||null,esterilizado:document.getElementById("p-esterilizado").value==="true",peso:parseFloat(document.getElementById("p-peso").value)||null,notas:document.getElementById("p-notas").value||null,propietario_id:parseInt(document.getElementById("p-propietario").value)})});showToast("Mascota actualizada");closeModal("paciente");frm.onsubmit=submitPaciente;loadMascotas()}catch(err){showToast(err.message,false)}};openModal("paciente")}catch(e){showToast(e.message,false)}}
async function deletePaciente(id){if(!confirm("Eliminar esta mascota?"))return;try{await api("/pacientes/"+id,{method:"DELETE"});showToast("Mascota eliminada");loadMascotas()}catch(e){showToast(e.message,false)}}
async function loadCitas(){try{const[c,m]=await Promise.all([api("/citas"),api("/pacientes")]);const pn={};m.forEach(p=>pn[p.id]=p.nombre);const stm={Pendiente:"bg-yellow-100 text-yellow-700",Confirmada:"bg-brand-100 text-brand-700",Completada:"bg-blue-100 text-blue-700",Cancelada:"bg-red-100 text-red-700"};document.getElementById("tabla-citas").innerHTML=c.map(ci=>
`<tr class="hover:bg-gray-50"><td class="px-4 py-3 text-sm">${new Date(ci.fecha).toLocaleDateString("es-PE",{day:"2-digit",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit"})}</td><td class="px-4 py-3 text-sm font-medium">${pn[ci.paciente_id]||"Mascota #"+ci.paciente_id}</td><td class="px-4 py-3 text-sm">${ci.motivo}</td><td class="px-4 py-3"><span class="text-xs px-2 py-0.5 rounded-full font-medium ${stm[ci.estado]||"bg-gray-100"}">${ci.estado}</span></td><td class="px-4 py-3 text-center space-x-2">${ci.estado==="Pendiente"?`<button onclick="aprobarCita(${ci.id})" class="text-brand-500 hover:text-brand-700 text-sm" title="Aprobar"><i class="fa-solid fa-check"></i></button>`:""}${ci.whatsapp_link?`<a href="${ci.whatsapp_link}" target="_blank" class="text-green-500 hover:text-green-700 text-sm" title="WhatsApp"><i class="fa-brands fa-whatsapp"></i></a>`:""}<button onclick="deleteCita(${ci.id})" class="text-red-500 hover:text-red-700 text-sm"><i class="fa-solid fa-trash"></i></button></td></tr>
`).join("")}catch(e){showToast(e.message,false)}}
async function submitCita(e){e.preventDefault();try{await api("/citas",{method:"POST",body:JSON.stringify({fecha:new Date(document.getElementById("c-fecha").value).toISOString(),motivo:document.getElementById("c-motivo").value,paciente_id:parseInt(document.getElementById("c-paciente").value)})});showToast("Cita agendada");closeModal("cita");loadCitas()}catch(e){showToast(e.message,false)}}
async function aprobarCita(id){try{await api("/citas/"+id+"/aprobar",{method:"POST"});showToast("Cita confirmada");loadCitas()}catch(e){showToast(e.message,false)}}
async function deleteCita(id){if(!confirm("Eliminar esta cita?"))return;try{await api("/citas/"+id,{method:"DELETE"});showToast("Cita eliminada");loadCitas()}catch(e){showToast(e.message,false)}}
async function loadHistorial(){try{const[m,p]=await Promise.all([api("/historial"),api("/pacientes")]);const pn={};p.forEach(x=>pn[x.id]=x.nombre);const fs=document.getElementById("h-filtro-paciente");if(fs.options.length<=1){p.forEach(x=>{const o=document.createElement("option");o.value=x.id;o.textContent=x.nombre;fs.appendChild(o)})}const fv=fs.value;const filtered=fv?m.filter(h=>h.paciente_id==fv):m;document.getElementById("tabla-historial").innerHTML=filtered.map(h=>
`<tr class="hover:bg-gray-50"><td class="px-4 py-3 text-sm">${new Date(h.fecha).toLocaleDateString("es-PE")}</td><td class="px-4 py-3 text-sm font-medium">${pn[h.paciente_id]||"?"}</td><td class="px-4 py-3 text-sm">${h.motivo_consulta}</td><td class="px-4 py-3 text-sm">${h.diagnostico||"-"}</td><td class="px-4 py-3 text-sm">${h.tratamiento||"-"}</td><td class="px-4 py-3 text-center space-x-2">${h.comprobante_id?`<span class="text-xs px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-700"><i class="fa-solid fa-check mr-0.5"></i>Facturado</span>`:`<button onclick="cobrarHistorial(${h.id})" class="text-emerald-600 hover:text-emerald-800 text-sm font-semibold" title="Cobrar / Facturar"><i class="fa-solid fa-file-invoice-dollar mr-0.5"></i>Cobrar</button>`}<button onclick="printHistorial(${h.id})" class="text-blue-500 hover:text-blue-700 text-sm" title="Imprimir"><i class="fa-solid fa-print"></i></button>${currentUser?.rol==="admin"?`<button onclick="deleteHistorial(${h.id})" class="text-red-500 hover:text-red-700 text-sm"><i class="fa-solid fa-trash"></i></button>`:""}</td></tr>
`).join("")}catch(e){showToast(e.message,false)}}
async function submitHistorial(e){e.preventDefault();const pid=parseInt(document.getElementById("h-paciente").value);try{await api("/pacientes/"+pid+"/historial",{method:"POST",body:JSON.stringify({motivo_consulta:document.getElementById("h-motivo").value,diagnostico:document.getElementById("h-diagnostico").value,tratamiento:document.getElementById("h-tratamiento").value||null,temperatura:document.getElementById("h-temp").value||null,frecuencia_cardiaca:document.getElementById("h-fc").value||null,peso_kg:parseFloat(document.getElementById("h-peso").value)||null,observaciones:document.getElementById("h-obs").value||null,proxima_cita:document.getElementById("h-proxima").value?new Date(document.getElementById("h-proxima").value).toISOString():null})});showToast("Consulta registrada");closeModal("historial");loadHistorial()}catch(e){showToast(e.message,false)}}
async function deleteHistorial(id){if(!confirm("Eliminar este registro?"))return;try{await api("/historial/"+id,{method:"DELETE"});showToast("Registro eliminado");loadHistorial()}catch(e){showToast(e.message,false)}}
async function cobrarHistorial(hid){
try{
const h=await api("/historial/"+hid);
const pac=await api("/pacientes/"+h.paciente_id);
const prop=await api("/propietarios/"+pac.propietario_id);
_cobrarHistorialId=hid;
await fillPropietarioSelect("cb-propietario");
const sel=document.getElementById("cb-propietario");
sel.value=prop.id;
sel.dispatchEvent(new Event("change"));
document.getElementById("cb-cliente").value=prop.nombre;
document.getElementById("cb-ruc").value=prop.ruc_dni||"";
document.getElementById("cb-tipo").value="boleta";
initDetalles();
await loadServiciosSelect();
const container=document.getElementById("detalles-container");
container.innerHTML="";
const consultas=serviciosCache.filter(s=>s.nombre.toLowerCase().includes("consulta"));
if(consultas.length){addDetalleRowWithService(consultas[0].id,consultas[0].precio,1)}
if(h.tratamiento&&h.tratamiento.toLowerCase().includes("vacuna")){const sv=serviciosCache.filter(s=>s.nombre.toLowerCase().includes("vacuna"));if(sv.length)addDetalleRowWithService(sv[0].id,sv[0].precio,1)}
if(h.tratamiento&&h.tratamiento.toLowerCase().includes("desparasit")){const sv=serviciosCache.filter(s=>s.nombre.toLowerCase().includes("desparasit"));if(sv.length)addDetalleRowWithService(sv[0].id,sv[0].precio,1)}
if(h.tratamiento&&h.tratamiento.toLowerCase().includes("profilaxis")){const sv=serviciosCache.filter(s=>s.nombre.toLowerCase().includes("profilaxis"));if(sv.length)addDetalleRowWithService(sv[0].id,sv[0].precio,1)}
if(h.tratamiento&&h.tratamiento.toLowerCase().includes("antibiot")){const sv=serviciosCache.filter(s=>s.nombre.toLowerCase().includes("amoxicilina"));if(sv.length)addDetalleRowWithService(sv[0].id,sv[0].precio,1)}
updateTotals();
openModal("comprobante");
}catch(e){showToast(e.message,false)}}
function addDetalleRowWithService(serviceId,price,qty){
const c=document.getElementById("detalles-container");
const r=document.createElement("div");
r.className="flex gap-2 items-end fade-in";
var opts=serviciosCache.map(function(s){return '<option value="'+s.id+'" data-precio="'+s.precio+'"'+(s.id===serviceId?" selected":"")+'">'+s.nombre+' - S/ '+s.precio.toFixed(2)+'</option>'}).join("");
r.innerHTML='<select class="det-sel border rounded-lg px-2 py-1.5 text-sm outline-none flex-1" onchange="onDetSelChange(this)"><option value="">Seleccionar...</option>'+opts+'</select><input type="number" class="det-cant border rounded-lg px-2 py-1.5 text-sm outline-none w-16" value="'+qty+'" min="1" onchange="updateTotals()"/><input type="number" class="det-prec border rounded-lg px-2 py-1.5 text-sm outline-none w-24" step="0.01" value="'+price.toFixed(2)+'" placeholder="S/" onchange="updateTotals()"/><button type="button" onclick="removeDetRow(this)" class="text-red-500 hover:text-red-700 px-1"><i class="fa-solid fa-xmark"></i></button>';
c.appendChild(r);updateTotals()}
async function printHistorial(id){try{const h=await api("/historial/"+id);const p=await api("/pacientes/"+h.paciente_id);const po=await api("/propietarios/"+p.propietario_id);const html=`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Historial - ${p.nombre}</title><style>body{font-family:Arial,sans-serif;padding:30px;font-size:13px}table{width:100%;border-collapse:collapse}td,th{border:1px solid #ddd;padding:6px 8px;text-align:left}.hdr{font-size:18px;font-weight:bold;border:none;padding:0 0 8px}.sub{color:#666;border:none;padding:0}.em{border:none;padding:0;padding-top:12px;font-weight:bold}</style></head><body><table><tr><td class="hdr" colspan="4">VetCare - Historial Clinico</td></tr><tr><td class="sub" colspan="4">${new Date(h.fecha).toLocaleString("es-PE")}</td></tr><tr><td colspan="4"></td></tr><tr><td class="em">Mascota:</td><td>${p.nombre} (${p.especie} - ${p.raza||"N/A"})</td><td class="em">Propietario:</td><td>${po.nombre} - ${po.telefono}</td></tr><tr><td class="em">Sexo:</td><td>${p.sexo||"N/A"}</td><td class="em">Peso:</td><td>${p.peso?p.peso+" kg":"N/A"}</td></tr><tr><td colspan="4"></td></tr><tr><td class="em">Motivo:</td><td colspan="3">${h.motivo_consulta}</td></tr><tr><td class="em">Diagnostico:</td><td colspan="3">${h.diagnostico||"-"}</td></tr><tr><td class="em">Tratamiento:</td><td colspan="3">${h.tratamiento||"-"}</td></tr><tr><td class="em">Temperatura:</td><td>${h.temperatura||"N/A"}</td><td class="em">Freq. Cardiaca:</td><td>${h.frecuencia_cardiaca||"N/A"}</td></tr><tr><td class="em">Peso(kg):</td><td>${h.peso_kg||"N/A"}</td><td></td><td></td></tr><tr><td class="em">Observaciones:</td><td colspan="3">${h.observaciones||"-"}</td></tr><tr><td class="em">Proxima Cita:</td><td colspan="3">${h.proxima_cita?new Date(h.proxima_cita).toLocaleString("es-PE"):"Sin programar"}</td></tr></table></body></html>`;const w=window.open("","","width=750,height=600");w.document.write(html);w.document.close();w.print()}catch(e){showToast(e.message,false)}}
async function loadInventario(){try{const d=await api("/inventario");const la=document.getElementById("stock-alerta");const bajos=d.filter(x=>x.stock<=x.stock_minimo);if(bajos.length){la.classList.remove("hidden");la.innerHTML=`<i class="fa-solid fa-triangle-exclamation mr-1"></i><strong>${bajos.length} articulos con stock bajo:</strong> ${bajos.map(x=>x.nombre+" ("+x.stock+")").join(", ")}`}else{la.classList.add("hidden")}document.getElementById("tabla-inventario").innerHTML=d.map(x=>
`<tr class="hover:bg-gray-50"><td class="px-4 py-3 text-sm font-medium">${x.nombre}</td><td class="px-4 py-3 text-sm">${x.categoria}</td><td class="px-4 py-3 text-sm ${x.stock<=x.stock_minimo?"text-red-600 font-bold":""}">${x.stock}</td><td class="px-4 py-3 text-sm">S/ ${x.precio_venta.toFixed(2)}</td><td class="px-4 py-3 text-sm">${x.proveedor||"-"}</td><td class="px-4 py-3 text-center space-x-2"><button onclick="openStockModal(${x.id},'${x.nombre.replace(/'/g,"\\'")}',${x.stock})" class="text-amber-500 hover:text-amber-700 text-sm" title="Ajustar stock"><i class="fa-solid fa-box-open"></i></button><button onclick="deleteInventario(${x.id})" class="text-red-500 hover:text-red-700 text-sm"><i class="fa-solid fa-trash"></i></button></td></tr>
`).join("")}catch(e){showToast(e.message,false)}}
async function submitInventario(e){e.preventDefault();try{await api("/inventario",{method:"POST",body:JSON.stringify({nombre:document.getElementById("i-nombre").value,categoria:document.getElementById("i-categoria").value,stock:parseInt(document.getElementById("i-stock").value)||0,stock_minimo:parseInt(document.getElementById("i-stock-min").value)||5,precio_compra:parseFloat(document.getElementById("i-pcomp").value)||0,precio_venta:parseFloat(document.getElementById("i-pvent").value)||0,proveedor:document.getElementById("i-proveedor").value||null,fecha_caducidad:document.getElementById("i-caducidad").value||null})});showToast("Articulo registrado");closeModal("inventario");loadInventario()}catch(e){showToast(e.message,false)}}
function openStockModal(id,nombre,actual){document.getElementById("s-id").value=id;document.getElementById("s-nombre").textContent="Articulo: "+nombre;document.getElementById("s-actual").textContent="Stock actual: "+actual;openModal("stock")}
async function submitStock(e){e.preventDefault();const id=document.getElementById("s-id").value;const cant=parseInt(document.getElementById("s-cantidad").value);try{await api("/inventario/"+id+"/stock",{method:"POST",body:JSON.stringify({cantidad:cant})});showToast("Stock actualizado");closeModal("stock");loadInventario()}catch(e){showToast(e.message,false)}}
async function deleteInventario(id){if(!confirm("Eliminar este articulo?"))return;try{await api("/inventario/"+id,{method:"DELETE"});showToast("Articulo eliminado");loadInventario()}catch(e){showToast(e.message,false)}}
let serviciosCache=[];
async function loadServiciosSelect(){try{serviciosCache=await api('/facturacion/servicios')}catch{serviciosCache=[]}}
async function submitServicio(e){e.preventDefault();try{await api('/facturacion/servicios',{method:'POST',body:JSON.stringify({nombre:document.getElementById('sv-nombre').value,tipo:document.getElementById('sv-tipo').value,precio:parseFloat(document.getElementById('sv-precio').value)})});showToast('Servicio/Producto creado');closeModal('servicio');loadServiciosSelect();loadComprobantes()}catch(e){showToast(e.message,false)}}
function initDetalles(){document.getElementById('detalles-container').innerHTML='';addDetalleRow()}
function addDetalleRow(){
  const c=document.getElementById('detalles-container');
  const r=document.createElement('div');
  r.className='flex gap-2 items-end fade-in';
  var opts=serviciosCache.map(function(s){return '<option value="'+s.id+'" data-precio="'+s.precio+'">'+s.nombre+' - S/ '+s.precio.toFixed(2)+'</option>'}).join('');
  r.innerHTML='<select class="det-sel border rounded-lg px-2 py-1.5 text-sm outline-none flex-1" onchange="onDetSelChange(this)"><option value="">Seleccionar...</option>'+opts+'</select><input type="number" class="det-cant border rounded-lg px-2 py-1.5 text-sm outline-none w-16" value="1" min="1" onchange="updateTotals()"/><input type="number" class="det-prec border rounded-lg px-2 py-1.5 text-sm outline-none w-24" step="0.01" placeholder="S/" onchange="updateTotals()"/><button type="button" onclick="removeDetRow(this)" class="text-red-500 hover:text-red-700 px-1"><i class="fa-solid fa-xmark"></i></button>';
  c.appendChild(r);updateTotals()
}
function onDetSelChange(sel){
  var opt=sel.options[sel.selectedIndex];
  var p=opt.getAttribute('data-precio')||'';
  var row=sel.closest('.flex');
  row.querySelector('.det-prec').value=p?parseFloat(p).toFixed(2):'';
  updateTotals()
}
function removeDetRow(btn){
  var c=document.getElementById('detalles-container');
  if(c.children.length<=1)return;
  btn.closest('.flex').remove();
  updateTotals()
}
function updateTotals(){
  var rows=document.querySelectorAll('#detalles-container .flex');
  var sub=0;
  rows.forEach(function(r){
    var c=parseFloat(r.querySelector('.det-cant').value)||0;
    var p=parseFloat(r.querySelector('.det-prec').value)||0;
    sub+=c*p
  });
  var igv=round2(sub*0.18);
  var total=round2(sub+igv);
  document.getElementById('cb-subtotal').textContent='S/ '+sub.toFixed(2);
  document.getElementById('cb-igv').textContent='S/ '+igv.toFixed(2);
  document.getElementById('cb-total').textContent='S/ '+total.toFixed(2)
}
function round2(n){return Math.round(n*100)/100}
async function submitComprobante(e){
  e.preventDefault();
  var rows=document.querySelectorAll('#detalles-container .flex');
  var detalles=[];
  for(var i=0;i<rows.length;i++){
    var sel=rows[i].querySelector('.det-sel').value;
    var cant=parseInt(rows[i].querySelector('.det-cant').value)||0;
    var prec=parseFloat(rows[i].querySelector('.det-prec').value)||0;
    if(sel && cant>0 && prec>0){detalles.push({servicio_producto_id:parseInt(sel),cantidad:cant,precio_unitario:prec})}
  }
  if(!detalles.length){showToast('Agrega al menos un item',false);return}
  var propVal=document.getElementById('cb-propietario').value;
  try{
    var comp=await api('/facturacion/comprobantes',{method:'POST',body:JSON.stringify({
      tipo_documento:document.getElementById('cb-tipo').value,
      cliente_nombre:document.getElementById('cb-cliente').value,
      cliente_ruc_dni:document.getElementById('cb-ruc').value||null,
      propietario_id:propVal?parseInt(propVal):null,
      detalles:detalles
    })});
    if(_cobrarHistorialId){
      var _hid=_cobrarHistorialId;
      try{await api('/historial/'+_hid+'/facturar',{method:'POST',body:JSON.stringify({comprobante_id:comp.id})})}catch{}
      _cobrarHistorialId=null;
      document.getElementById('cb-cliente').readOnly=false;
      document.getElementById('cb-ruc').readOnly=false;
      showToast('Comprobante generado');closeModal('comprobante');loadComprobantes();loadHistorial();return
    }
    document.getElementById('cb-cliente').readOnly=false;
    document.getElementById('cb-ruc').readOnly=false;
    showToast('Comprobante generado');closeModal('comprobante');loadComprobantes()
  }catch(e){showToast(e.message,false)}
}
async function loadComprobantes(){
  try{
    var d=await api('/facturacion/comprobantes');
    var tl={boleta:'bg-blue-100 text-blue-700',factura:'bg-purple-100 text-purple-700'};
    var sl={Pagado:'bg-brand-100 text-brand-700',Anulado:'bg-red-100 text-red-700'};
    var ad=currentUser&&currentUser.rol==='admin';
    document.getElementById('tabla-comprobantes').innerHTML=d.map(function(c){
      var num=c.serie+'-'+String(c.numero).padStart(5,'0');
      var dt=new Date(c.fecha_emision).toLocaleDateString('es-PE');
      return '<tr class="hover:bg-gray-50"><td class="px-4 py-3 text-sm font-mono font-bold">'+num+'</td><td class="px-4 py-3"><span class="text-xs px-2 py-0.5 rounded-full font-medium '+(tl[c.tipo_documento]||'bg-gray-100')+'">'+c.tipo_documento.toUpperCase()+'</span></td><td class="px-4 py-3 text-sm">'+c.cliente_nombre+'</td><td class="px-4 py-3 text-sm">'+dt+'</td><td class="px-4 py-3 text-sm font-bold">S/ '+c.total.toFixed(2)+'</td><td class="px-4 py-3"><span class="text-xs px-2 py-0.5 rounded-full font-medium '+(sl[c.estado]||'bg-gray-100')+'">'+c.estado+'</span></td><td class="px-4 py-3 text-center space-x-2"><button onclick="printReceipt('+c.id+')" class="text-blue-500 hover:text-blue-700 text-sm" title="Imprimir"><i class="fa-solid fa-print"></i></button>'+(ad&&c.estado!=='Anulado'?'<button onclick="anularComprobante('+c.id+')" class="text-red-500 hover:text-red-700 text-sm" title="Anular"><i class="fa-solid fa-ban"></i></button>':'')+'</td></tr>'
    }).join('')
  }catch(e){showToast(e.message,false)}
}
async function anularComprobante(id){
  if(!confirm('Anular este comprobante?'))return;
  try{
    await api('/facturacion/comprobantes/'+id+'/anular',{method:'POST'});
    showToast('Comprobante anulado');loadComprobantes()
  }catch(e){showToast(e.message,false)}
}
async function printReceipt(id){
  try{
    var c=await api('/facturacion/comprobantes/'+id);
    var num=c.serie+'-'+String(c.numero).padStart(5,'0');
    var dt=new Date(c.fecha_emision).toLocaleString('es-PE');
    var tipoLabel=c.tipo_documento==='boleta'?'BOLETA DE VENTA':'FACTURA';
    var rows='';
    if(c.detalles&&c.detalles.length){
      for(var i=0;i<c.detalles.length;i++){
        var d=c.detalles[i];
        var sv=serviciosCache.find(function(s){return s.id===d.servicio_producto_id});
        var nm=sv?sv.nombre:'Item #'+d.servicio_producto_id;
        rows+='<tr><td>'+nm+'</td><td style="text-align:center">'+d.cantidad+'</td><td style="text-align:right">S/ '+d.precio_unitario.toFixed(2)+'</td><td style="text-align:right">S/ '+d.subtotal.toFixed(2)+'</td></tr>';
      }
    }
    var rucDni=c.cliente_ruc_dni||'-';
    var h='<html><head><meta charset="utf-8"><title>'+num+'</title>';
    h+='<style>body{font-family:monospace;padding:20px;font-size:12px;max-width:350px;margin:0 auto}';
    h+='table{width:100%;border-collapse:collapse;margin:10px 0}td,th{padding:3px 4px}';
    h+='th{border-bottom:1px solid #000}.c{text-align:center}.r{text-align:right}';
    h+='.b{font-weight:bold}.hr{border-top:1px dashed #000;margin:8px 0}.tot{font-size:14px;font-weight:bold}</style></head><body>';
    h+='<div class="c b">VETCARE - CLINICA VETERINARIA</div>';
    h+='<div class="c">RUC: 10456789010</div>';
    h+='<div class="c">Av. Principal 123, Lima</div>';
    h+='<div class="c">Tel: 982127669</div>';
    h+='<div class="hr"></div>';
    h+='<div class="c b">'+tipoLabel+'</div>';
    h+='<div class="c">Serie: '+num+'</div>';
    h+='<div class="c">Fecha: '+dt+'</div>';
    h+='<div class="hr"></div>';
    h+='<div>Cliente: <b>'+c.cliente_nombre+'</b></div>';
    h+='<div>DNI/RUC: '+rucDni+'</div>';
    h+='<div class="hr"></div>';
    h+='<table><thead><tr><th>Item</th><th style="text-align:center">Cant</th><th style="text-align:right">P.Unit</th><th style="text-align:right">Subtot</th></tr></thead>';
    h+='<tbody>'+rows+'</tbody></table>';
    h+='<div class="hr"></div>';
    h+='<div class="r">Subtotal: S/ '+c.subtotal.toFixed(2)+'</div>';
    h+='<div class="r">IGV (18%): S/ '+c.igv.toFixed(2)+'</div>';
    h+='<div class="r tot">TOTAL: S/ '+c.total.toFixed(2)+'</div>';
    h+='<div class="hr"></div>';
    h+='<div class="c" style="font-size:10px;margin-top:10px">Gracias por su preferencia</div>';
    h+='<div class="c" style="font-size:10px">www.vetcare.com</div>';
    h+='</body></html>';
    var w=window.open('','',  'width=400,height=600');w.document.write(h);w.document.close();w.print()
  }catch(e){showToast(e.message,false)}
}
document.addEventListener('DOMContentLoaded', function(){
  tryAutoLogin();
})
