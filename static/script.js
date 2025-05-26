const conv = document.getElementById('conversation');
const msgInput = document.getElementById('message');
document.getElementById('send').onclick = async () => {
  const text = msgInput.value.trim();
  if (!text) return;
  conv.innerHTML += `<p><strong>Ty:</strong> ${text}</p>`;
  msgInput.value = '';
  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({message: text})
    });
    const data = await res.json();
    const reply = data.reply || data.error;
    conv.innerHTML += `<p><strong>Winston:</strong> ${reply}</p>`;
    conv.scrollTop = conv.scrollHeight;
  } catch (err) {
    conv.innerHTML += `<p style="color:red;"><strong>Chyba:</strong> ${err}</p>`;
  }
};
