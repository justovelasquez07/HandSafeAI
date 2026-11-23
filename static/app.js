
const $ = id => document.getElementById(id);

let active = false;
let toastTimer;

function toast(msg) {
    $('toast').textContent = msg;
    $('toast').classList.add('show');

    clearTimeout(toastTimer);

    toastTimer = setTimeout(
        () => $('toast').classList.remove('show'),
        3000
    );
}

async function api(url, body) {
    const response = await fetch(
        url,
        body
            ? {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(body)
            }
            : {}
    );

    return response.json();
}

async function scan() {
    $('scanBtn').disabled = true;
    $('scanBtn').textContent = 'Buscando...';

    try {
        const data = await api('/api/cameras');
        const select = $('cameraSelect');

        select.innerHTML = '';

        if (!data.cameras.length) {
            select.innerHTML =
                '<option value="">No se encontraron cámaras</option>';

            toast('No se encontraron cámaras disponibles');
        } else {
            data.cameras.forEach(camera => {
                const option = document.createElement('option');
                option.value = camera.index;
                option.textContent = camera.label;
                select.appendChild(option);
            });

            toast(`${data.cameras.length} cámara(s) encontrada(s)`);
        }
    } catch (error) {
        toast('No se pudo buscar cámaras');
    } finally {
        $('scanBtn').disabled = false;
        $('scanBtn').textContent = '↻ Buscar';
    }
}

async function start() {
    const value = $('cameraSelect').value;

    if (value === '') {
        toast('Primero busca y selecciona una cámara');
        return;
    }

    $('startBtn').disabled = true;

    try {
        const data = await api('/api/start', {
            index: Number(value)
        });

        if (!data.ok) {
            toast(data.state.error || 'No se pudo iniciar la cámara');
            return;
        }

        active = true;

        $('video').src = '/video?t=' + Date.now();
        $('video').style.display = 'block';
        $('placeholder').style.display = 'none';

        $('status').textContent = 'CÁMARA ACTIVA';
        $('cameraTag').textContent = 'Cámara ' + value;

        $('stopBtn').disabled = false;

        toast('Cámara iniciada correctamente');

    } catch (error) {
        toast('Error al iniciar la cámara');
    } finally {
        $('startBtn').disabled = active;
    }
}

async function stop() {
    await api('/api/stop', {});

    active = false;

    $('video').removeAttribute('src');
    $('video').style.display = 'none';
    $('placeholder').style.display = 'flex';

    $('status').textContent = 'CÁMARA DETENIDA';
    $('cameraTag').textContent = 'Sin cámara';

    $('startBtn').disabled = false;
    $('stopBtn').disabled = true;

    resetAlphabet();

    toast('Cámara detenida');
}

function resetAlphabet() {
    $('alphabetLetter').textContent = '—';
    $('alphabetDescription').textContent = 'Esperando una seña...';
    $('alphabetConfidence').textContent = '0%';
    $('alphabetConfidenceBar').style.width = '0%';
}

async function state() {
    try {
        const data = await api('/api/state');

        $('gesture').textContent = data.gesture;
        $('category').textContent = data.category;
        $('description').textContent = data.description;

        const confidence = Math.round((data.confidence || 0) * 100);

        $('confidence').textContent = confidence + '%';
        $('confidenceBar').style.width = confidence + '%';

        $('detections').textContent = data.detections;
        $('voiceToggle').checked = data.voice_enabled;

        // Resultado del modelo del alfabeto
        const letter = data.alphabet_letter || '';

        if (letter) {
            $('alphabetLetter').textContent = letter;
            $('alphabetDescription').textContent =
                'Posible seña identificada: ' + letter;
        } else {
            $('alphabetLetter').textContent = '—';
            $('alphabetDescription').textContent =
                data.alphabet_status || 'Esperando una seña...';
        }

        const alphabetConfidence = Math.round(
            (data.alphabet_confidence || 0) * 100
        );

        $('alphabetConfidence').textContent =
            alphabetConfidence + '%';

        $('alphabetConfidenceBar').style.width =
            alphabetConfidence + '%';

        $('alphabetStatus').textContent =
            data.alphabet_model_loaded
                ? 'Modelo cargado'
                : 'Modelo no disponible';

        if (data.error) {
            toast(data.error);
        }

    } catch (error) {
        // El servidor puede estar iniciándose o reiniciándose.
    }
}

async function history() {
    try {
        const data = await api('/api/history');
        const body = $('history');

        if (!data.history.length) {
            body.innerHTML =
                '<tr><td colspan="4" class="empty">' +
                'Todavía no hay detecciones registradas.</td></tr>';
            return;
        }

        body.innerHTML = data.history.slice().reverse().map(item => `
            <tr>
                <td>${item.timestamp.replace('T', ' ')}</td>
                <td>${item.gesture}</td>
                <td>${item.category}</td>
                <td>${Math.round(item.confidence * 100)}%</td>
            </tr>
        `).join('');

    } catch (error) {
        // Se intentará actualizar nuevamente.
    }
}

$('scanBtn').onclick = scan;
$('startBtn').onclick = start;
$('stopBtn').onclick = stop;
$('refreshHistory').onclick = history;

$('voiceToggle').onchange = async event => {
    await api('/api/voice', {
        enabled: event.target.checked
    });

    toast(
        event.target.checked
            ? 'Voz activada'
            : 'Voz desactivada'
    );
};

scan();
history();

setInterval(state, 700);
setInterval(history, 5000);
