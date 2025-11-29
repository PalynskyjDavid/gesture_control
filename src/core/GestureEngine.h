#pragma once
#include <QObject>
#include <QTcpSocket>
#include <QString>
#include <QVector>
#include "../common/Types.h"

class GestureEngine : public QObject
{
    Q_OBJECT
public:
    explicit GestureEngine(QObject *parent = nullptr);

    void start();
    void stop();

signals:
    void connectionStatusChanged(const QString &status);

    // NEW: emit list of hands
    void handsUpdated(const QVector<HandInfo> &hands);

private slots:
    void onConnected();
    void onDisconnected();
    void onError(QAbstractSocket::SocketError);
    void onReadyRead();

private:
    void processJson(const QString &jsonStr);

    QTcpSocket socket_;
    QString buffer_;
};
