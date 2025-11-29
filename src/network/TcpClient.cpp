#include "TcpClient.h"

TcpClient::TcpClient(QObject *parent)
    : QObject(parent)
{
    connect(&socket_, &QTcpSocket::connected,
            this, &TcpClient::onConnected);

    connect(&socket_, &QTcpSocket::disconnected,
            this, &TcpClient::onDisconnected);

    connect(&socket_, &QTcpSocket::readyRead,
            this, &TcpClient::onReadyRead);

    connect(&socket_,
            QOverload<QAbstractSocket::SocketError>::of(&QTcpSocket::errorOccurred),
            this, &TcpClient::onError);
}

void TcpClient::connectToServer(const QString &host, int port)
{
    socket_.connectToHost(host, port);
}

void TcpClient::disconnectFromServer()
{
    socket_.disconnectFromHost();
}

void TcpClient::sendLine(const QString &line)
{
    socket_.write(line.toUtf8());
    socket_.write("\n");
}

void TcpClient::onConnected()
{
    emit connected();
}

void TcpClient::onDisconnected()
{
    emit disconnected();
}

void TcpClient::onError(QAbstractSocket::SocketError)
{
    emit connectionError(socket_.errorString());
}

void TcpClient::onReadyRead()
{
    buffer_.append(QString::fromUtf8(socket_.readAll()));

    while (true)
    {
        int idx = buffer_.indexOf('\n');
        if (idx < 0)
            return;

        QString line = buffer_.left(idx).trimmed();
        buffer_.remove(0, idx + 1);

        if (!line.isEmpty())
            emit lineReceived(line);
    }
}
