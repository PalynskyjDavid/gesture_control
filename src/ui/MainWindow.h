#pragma once

#include <QMainWindow>
#include <QMap>

class QListWidget;
class QListWidgetItem;
class QComboBox;
class QPushButton;
class QLabel;
class QCheckBox;

#include "../core/GestureEngine.h"
#include "../platform/InputSimulator.h"

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = nullptr);

    void initialize(); // called after injection

    void setInputSimulator(InputSimulator *sim) { inputSim_ = sim; }
    void setGestureEngine(GestureEngine *eng);

private slots:
    void onGestureSelected(QListWidgetItem *item);
    void onBindActionChanged(int index);
    void onTestActionClicked();
    void onTrackingToggled(bool checked);

    void onHandsUpdated(const QVector<HandInfo> &hands);
    void onConnectionStatusChanged(const QString &status);

    void openSettingsDialog();
    void onSettingsSaved();

private:
    void setupUi();
    void loadDefaultGestures();
    void applyBinding(const QString &hand,
                      const QString &gestureName,
                      const QString &actionName);
    QString makeBindingKey(const QString &hand,
                           const QString &gesture) const;

private:
    QListWidget *gestureList_ = nullptr;
    QLabel *gestureLabel_ = nullptr;
    QComboBox *actionCombo_ = nullptr;
    QPushButton *testButton_ = nullptr;
    QCheckBox *trackingCheckBox_ = nullptr;
    QLabel *statusLabel_ = nullptr;

    InputSimulator *inputSim_ = nullptr;
    GestureEngine *gestureEngine_ = nullptr;

    QMap<QString, QString> gestureBindings_;
    QMap<QString, HandInfo> lastHands_;
};
