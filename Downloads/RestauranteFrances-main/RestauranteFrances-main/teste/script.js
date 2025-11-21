const calendar = document.getElementById('calendar');
const timeSlots = document.getElementById('time-slots');
const monthYear = document.getElementById('monthYear');
const prevMonthBtn = document.getElementById('prevMonth');
const nextMonthBtn = document.getElementById('nextMonth');

const today = new Date();
let selectedDate = today; // dia atual selecionado

let currentMonth = today.getMonth();
let currentYear = today.getFullYear();

const horarios = [
    "09:00 - 10:00",
    "10:00 - 12:00",
    "12:00 - 13:00",
    "13:00 - 14:00",
    "14:00 - 15:00",
    "15:00 - 16:00",
    "16:00 - 17:00"
];

function generateCalendar(year, month) {
    calendar.innerHTML = '';

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    const startDayOfWeek = firstDay.getDay();
    const totalDays = lastDay.getDate();

    const options = { month: 'long', year: 'numeric' };
    monthYear.textContent = firstDay.toLocaleDateString('pt-BR', options);

    for (let i = 0; i < startDayOfWeek; i++) {
        const emptyCell = document.createElement('div');
        calendar.appendChild(emptyCell);
    }

    for (let day = 1; day <= totalDays; day++) {
        const date = new Date(year, month, day);
        const dayElement = document.createElement('div');
        dayElement.textContent = day;
        dayElement.classList.add('day');

        if (date < new Date(today.getFullYear(), today.getMonth(), today.getDate())) {
            dayElement.classList.add('disabled');
        } else {
            dayElement.addEventListener('click', () => selectDay(dayElement, date));
        }

        if (
            (year === today.getFullYear() && month === today.getMonth() && day === today.getDate()) ||
            (selectedDate && date.getTime() === selectedDate.getTime())
        ) {
            dayElement.classList.add('selected');
            selectedDate = date;
            showTimeSlots();
        }

        calendar.appendChild(dayElement);
    }
}

function showTimeSlots() {
    timeSlots.innerHTML = '';
    horarios.forEach(time => {
        const li = document.createElement('li');
        li.textContent = time;
        li.classList.add('list-group-item');
        timeSlots.appendChild(li);
    });
}

function selectDay(dayElement, date) {
    document.querySelectorAll('.day.selected').forEach(el => el.classList.remove('selected'));
    dayElement.classList.add('selected');
    selectedDate = date;
    showTimeSlots();
}

prevMonthBtn.addEventListener('click', () => {
    currentMonth--;
    if (currentMonth < 0) {
        currentMonth = 11;
        currentYear--;
    }
    generateCalendar(currentYear, currentMonth);
});

nextMonthBtn.addEventListener('click', () => {
    currentMonth++;
    if (currentMonth > 11) {
        currentMonth = 0;
        currentYear++;
    }
    generateCalendar(currentYear, currentMonth);
});

generateCalendar(currentYear, currentMonth);
