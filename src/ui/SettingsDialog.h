#pragma once
#include <QDialog>

QT_BEGIN_NAMESPACE
class QDoubleSpinBox;
class QSpinBox;
class QComboBox;
class QCheckBox;
class QPushButton;
class QLabel;
QT_END_NAMESPACE

class SettingsDialog : public QDialog
{
    Q_OBJECT
public:
    explicit SettingsDialog(QWidget *parent = nullptr);

signals:
    void configSaved();

public slots:
    void openSettingsDialog();
    void onSettingsSaved();

private slots:
    void onApply();
    void onReset();

private:
    // classifier
    QSpinBox *historySpin_;
    QDoubleSpinBox *swipeSpin_;
    QDoubleSpinBox *zoomSpin_;
    QDoubleSpinBox *dragSpin_;
    QDoubleSpinBox *pinchSpin_;
    QDoubleSpinBox *thumbAngleSpin_;

    // multi-hand
    QCheckBox *twoHandEnable_;
    QSpinBox *twoHandWindow_;
    QDoubleSpinBox *twoHandThresh_;

    // smoothing
    QComboBox *smoothingModeCombo_;
    QDoubleSpinBox *emaAlphaSpin_;
    QDoubleSpinBox *hystEnterSpin_;
    QDoubleSpinBox *hystExitSpin_;

    // debug
    QCheckBox *drawLandmarks_;
    QCheckBox *showFps_;
    QSpinBox *fpsWindowSpin_;

    QPushButton *applyBtn_;
    QPushButton *resetBtn_;

    void loadFromConfig();
    void writeToConfigFile();
};
