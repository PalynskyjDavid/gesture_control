#pragma once
#include <QObject>
#include <QTcpSocket>

/**
 * TcpClient
 * -----------------------
 * Encapsulates a QTcpSocket and exposes:
 *   - connectToServer()
 *   - disconnect()
 *   - sending text lines
 *   - receiving data as signals
 */

class TcpClient : public QObject
{
    Q_OBJECT

public:
    explicit TcpClient(QObject *parent = nullptr);

    void connectToServer(const QString &host, int port);
    void disconnectFromServer();
    void sendLine(const QString &line);

signals:
    void connected();
    void disconnected();
    void lineReceived(QString);
    void connectionError(QString);

private slots:
    void onConnected();
    void onDisconnected();
    void onReadyRead();
    void onError(QAbstractSocket::SocketError);

private:
    QTcpSocket socket_;
    QString buffer_;
};
