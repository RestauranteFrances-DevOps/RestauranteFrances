require('dotenv').config();
const express = require('express');
const cors = require('cors');
const mysql = require('mysql2');

const app = express();
app.use(cors());
app.use(express.json());

// ==================== CONEXÃO BANCO ====================
const db = mysql.createConnection({
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME
});

db.connect(err => {
    if (err) {
        console.log('Erro ao conectar ao MySQL:', err);
        return;
    }
    console.log('Conectado ao MySQL!');
});

// ==================== ROTA BUSCAR HORÁRIOS ====================
app.get('/reservas/:dia', (req, res) => {
    const dia = req.params.dia;

    const sql = "SELECT horario FROM reservas WHERE dia = ?";
    db.query(sql, [dia], (err, results) => {
        if (err) {
            console.error("Erro ao buscar horários reservados:", err);
            return res.status(500).json({ error: "Erro ao buscar horários" });
        }

        const horariosReservados = results.map(row => row.horario);
        res.json({ horariosReservados });
    });
});

// ==================== ROTA SALVAR RESERVA ====================
app.post('/reserva', (req, res) => {
    const { nome, email, cpf, telefone, calendarioDia, calendarioHorario } = req.body;

    const sql = `
        INSERT INTO reservas (nome, email, cpf, telefone, dia, horario)
        VALUES (?, ?, ?, ?, ?, ?)
    `;

    db.query(sql, [nome, email, cpf, telefone, calendarioDia, calendarioHorario], (err, result) => {
        if (err) {
            console.log('Erro ao inserir:', err);
            return res.status(500).json({ error: 'Erro ao salvar reserva' });
        }
        res.json({ message: 'Reserva salva com sucesso!' });
    });
});

// ==================== INICIAR SERVIDOR ====================
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Servidor rodando na porta ${PORT}`);
});
