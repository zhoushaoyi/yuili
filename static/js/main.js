const btnStart = document.getElementById('btnStart')
const btnStop = document.getElementById('btnStop')
const form = document.getElementById('controlForm')
const logBox = document.getElementById('logBox')
const alertsList = document.getElementById('alertsList')
let pollTimer = null

btnStart.addEventListener('click', async ()=>{
  const data = new FormData(form)
  const res = await fetch('/start_detection', {method:'POST', body:data})
  const j = await res.json()
  appendLog(JSON.stringify(j))
  if(j.status==='success'){
    btnStart.disabled = true
    btnStop.disabled = false
    startPolling()
  }
})

btnStop.addEventListener('click', async ()=>{
  const res = await fetch('/stop_detection', {method:'POST'})
  const j = await res.json()
  appendLog(JSON.stringify(j))
  btnStart.disabled = false
  btnStop.disabled = true
  stopPolling()
})

function appendLog(s){
  const t = new Date().toLocaleTimeString()
  logBox.textContent += `[${t}] ${s}\n`
  logBox.scrollTop = logBox.scrollHeight
}

async function pollLogs(){
  try{
    const res = await fetch('/get_logs')
    const j = await res.json()
    if(j.logs){
      j.logs.slice(-10).forEach(l=> appendLog(l))
    }
    // alerts
    const ares = await fetch('/alerts')
    const al = await ares.json()
    alertsList.innerHTML = ''
    al.forEach((it,idx)=>{
      const li = document.createElement('li')
      li.textContent = `${it.time} - ${JSON.stringify(it.alerts)}`
      alertsList.appendChild(li)
    })
  }catch(e){
    appendLog('poll error: '+e)
  }
}

function startPolling(){
  if(pollTimer) return
  pollTimer = setInterval(pollLogs, 2000)
}
function stopPolling(){
  if(pollTimer){clearInterval(pollTimer);pollTimer=null}
}

// auto poll if page loaded
startPolling()
