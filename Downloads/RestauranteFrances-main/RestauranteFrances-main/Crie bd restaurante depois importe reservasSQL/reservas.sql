-- phpMyAdmin SQL Dump
-- version 5.2.0
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 17-Nov-2025 às 07:22
-- Versão do servidor: 10.4.24-MariaDB
-- versão do PHP: 7.4.29

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `restaurante`
--

-- --------------------------------------------------------

--
-- Estrutura da tabela `reservas`
--

CREATE TABLE `reservas` (
  `id` int(11) NOT NULL,
  `nome` varchar(100) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `cpf` varchar(20) DEFAULT NULL,
  `telefone` varchar(20) DEFAULT NULL,
  `dia` varchar(20) DEFAULT NULL,
  `horario` varchar(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Extraindo dados da tabela `reservas`
--

INSERT INTO `reservas` (`id`, `nome`, `email`, `cpf`, `telefone`, `dia`, `horario`) VALUES
(1, 'e', 'eee', 'ebdh', '111', '17/11/2025', '09:00 - 10:00'),
(2, 'kdnnjd', 'pedro', 'eds', '11', '18/11/2025', ''),
(3, 'j', 'm', 'u', '7', '17/11/2025', '09:00 - 10:00'),
(4, 'e', 'e', 'e', '1', '17/11/2025', '09:00 - 10:00'),
(5, 'hh', 'jehje', 'jh', '222', '17/11/2025', '09:00 - 10:00'),
(6, 'dd', 'dd', 'dddd', '222', '17/11/2025', '09:00 - 10:00'),
(7, 'x', 'd', 'xx', '221', '17/11/2025', '10:00 - 12:00'),
(8, 'x', 'd', 'xx', '221', '17/11/2025', '09:00 - 10:00'),
(9, 'dnbdkh', 'jhkjf', 'fhbb', '22333', '19/11/2025', '09:00 - 10:00'),
(10, 'dkbbhc', 'dhdvjhcv', 'cojncjb', '2', '17/11/2025', '15:00 - 16:00'),
(11, 'ddd', 'd', '222', '222', '20/11/2025', '10:00 - 12:00');

--
-- Índices para tabelas despejadas
--

--
-- Índices para tabela `reservas`
--
ALTER TABLE `reservas`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT de tabelas despejadas
--

--
-- AUTO_INCREMENT de tabela `reservas`
--
ALTER TABLE `reservas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
